#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# pylint: disable=no-member
"""
Created on Tue May 16 11:42:45 2017
@author: github.com/Quantmatic
"""
import datetime
import time
import pandas as pd
import TTR
import amipy
from amipy import Amipy

def _months(_df):
    months = _df.index.month
    return pd.Series(months, index=_df.index, name='months', dtype=int)

def _days(_df):
    days = _df.index.day
    return pd.Series(days, index=_df.index, name='days', dtype=int)


class BoliingerCMF(object):
    ''' Bollinger CMF '''
    def __init__(self, context):
        self.__dict__.update(context.__dict__)

    def Run(self, data):
        ''' analyze OHLCV matrix and generate signals '''
        ohlc = data[:][['open', 'high', 'low', 'close', 'volume']]
        ptimer = time.time()

        bbperiod = 25
        bbupper, bblower, bbmid = TTR.bollinger(ohlc.close, bbperiod, 2)

        cmf_period = bbperiod*2
        cmf = TTR.cmf(ohlc, cmf_period)

        days = _days(ohlc)
        months = _months(ohlc)
        #*** no trading during Christmas season ***#
        notradetime = (months.shift(1) == 12) & (days.shift(1) > 23)

        buysignal1 = (cmf.shift(1) > 0) & \
                     (abs(ohlc.close.shift(1)-bblower.shift(1)) < 5*self.tick_size)
        buy = (buysignal1) & (notradetime == 0)

        shortsignal1 = (cmf.shift(1) < 0) & \
                       (abs(ohlc.close.shift(1)-bbupper.shift(1)) < 5*self.tick_size)
        short = (shortsignal1) & (notradetime == 0)

        short[:self.warmup_bars] = False #remove signals from warmup bars
        buy[:self.warmup_bars] = False   #remove signals from warmup bars

        stopcover = (ohlc.open.shift(1) > bbmid.shift(1)) & \
                    (ohlc.close.shift(1) < bbmid.shift(1))

        stopsell = (ohlc.open.shift(1) < bbmid.shift(1)) & \
                   (ohlc.close.shift(1) > bbmid.shift(1))

        cover = buy | stopcover
        sell = short | stopsell

        buy = amipy.ex_rem(buy, sell, 1) #remove excess signals
        short = amipy.ex_rem(short, cover, 1) #remove excess signals

        buyprice = ohlc.open + (2*self.tick_size) ## *adjust for slippage
        shortprice = ohlc.open - (2*self.tick_size) ## *adjust for slippage
        coverprice = ohlc.open + (1*self.tick_size)
        sellprice = ohlc.open - (1*self.tick_size)

        backtest = Amipy(self, ohlc)

        backtest.run(buy, short, sell, cover, buyprice,
                     shortprice, sellprice, coverprice)

        print 'Backtest finished in ' + str(time.time()-ptimer) + ' seconds.\n'
        backtest.analyze_results(0.0025)
        backtest.analyze_results_ffn(0.0025)
        backtest.plot_trades(ohlc.index[0].year, ohlc.index[-1].year)
        backtest.annual_gains(ohlc.index[0].year, ohlc.index[-1].year)


class Context(object):
    ''' backtest context '''
    def __init__(self):
        self.symbol = '@ES#4H'  #*** e-mini SP 240min continuous ***#
        self.dbase = 'FUTURE'
        self.starting_equity = 100000.00
        self.margin_required = 5500.0
        self.tick_size = 0.25
        self.tick_value = 12.5
        self.risk = 0.2
        self.warmup_bars = 500
        self.commission = 4.50

if __name__ == '__main__':
    ##########################################################################
    START_DATE = datetime.datetime(2011, 1, 2)
    END_DATE = datetime.datetime(2016, 12, 31)
    OBJ = Context()
    OHLC = amipy.mongo_grab(OBJ.symbol, OBJ.dbase, START_DATE, END_DATE)

    STRAT = BoliingerCMF(OBJ)

    STRAT.Run(OHLC)
