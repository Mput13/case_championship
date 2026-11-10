#!/usr/bin/env python3
"""Render static research figures from this package, without browser or network."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
OUT = BASE / 'illustrations'
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':12, 'axes.spines.top':False,
                     'axes.spines.right':False, 'axes.spines.left':False})
RED = '#c21f3c'
BLUE = '#28506b'
GRAY = '#8c9298'
TEXT = '#252b31'


def market():
    fig = plt.figure(figsize=(14,8), facecolor='white')
    fig.text(.07,.94,'Масштаб цели №2',fontsize=25,weight='bold',color=TEXT)
    fig.text(.07,.895,'2025 год · отдельные перевозчики · млн перевезённых пассажиров',fontsize=14,color=TEXT)
    ax=fig.add_axes([.24,.32,.67,.50])
    names=['1. Аэрофлот','2. Победа','3. Сибирь / S7','4. Россия','Red Wings*']
    values=[29.5473,13.8,12.8,12,2.7]
    colors=[GRAY,RED,GRAY,GRAY,BLUE]
    ys=list(range(len(values)))
    ax.barh(ys,values,color=colors,height=.56)
    ax.set_yticks(ys,names)
    ax.invert_yaxis()
    ax.set_xlim(0,32)
    ax.set_xticks([0,5,10,15,20,25,30])
    ax.grid(axis='x',color='#e8ebed',linewidth=.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y',length=0,pad=14)
    for y,v in zip(ys,values):
        ax.text(v+.35,y,f'{v:.2f}'.replace('.',','),va='center',weight='bold',color=TEXT)
    fig.text(.07,.235,'11,1 млн',fontsize=27,weight='bold',color=RED)
    fig.text(.265,.242,'разрыв до опубликованного объёма «Победы»; около 5,1× базы RW',fontsize=13,color=TEXT)
    fig.text(.07,.177,'108,85 млн — пассажиры всех российских перевозчиков за 2025; доля RW ≈ 2,48%.',fontsize=12,color=TEXT)
    fig.text(.07,.125,'Пятое место — Уральские авиалинии; первичный годовой объём здесь не получен.\n* Точное место RW по полному первичному списку не установлено. Показана выборка компаний.',fontsize=10.5,color='#555e66')
    fig.text(.07,.055,'Источники: Росавиация 30.01.2026; годовые релизы Аэрофлота/Победы (АвиаПорт), S7, России, RW.\nГруппа Аэрофлот — 55,34 млн, включает три показанные компании; повторно не складывать. Не прогноз 2027–2028.',fontsize=10,color='#555e66')
    fig.savefig(OUT/'S01_market_scale.png',dpi=160)
    plt.close(fig)


def resource():
    rows=[r for r in csv.DictReader((BASE/'resource_scale.csv').open())
          if r['target_passenger_segments_per_year']=='13800000']
    fig=plt.figure(figsize=(14,8),facecolor='white')
    fig.text(.07,.94,'Ресурс для добавочных 11,1 млн сегментов в год',fontsize=23,weight='bold',color=TEXT)
    fig.text(.07,.887,'Сценарный эквивалент дополнительных списочных самолётов, стандартный год 365 дней',fontsize=13,color=TEXT)
    ax=fig.add_axes([.28,.29,.62,.50])
    names=['100 мест · осторожный','100 мест · базовый','194 места','412 мест']
    values=[int(x['additional_stock_equivalent_ceil']) for x in rows]
    ax.barh(range(4),values,color=[GRAY,RED,BLUE,BLUE],height=.54)
    ax.set_yticks(range(4),names)
    ax.invert_yaxis()
    ax.set_xlim(0,170)
    ax.grid(axis='x',color='#e8ebed',linewidth=.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y',length=0,pad=12)
    for y,r in enumerate(rows):
        v=values[y]
        ax.text(v+2,y,str(v),va='center',weight='bold',fontsize=17,color=TEXT)
        label=(f"LF {float(r['load_factor'])*100:.0f}% · плечо {float(r['block_hours_per_leg']):g} ч · "
               f"{float(r['productive_hours_per_active_day']):g} ч/активный день · доступность {float(r['availability_including_reserve'])*100:.0f}%")
        ax.text(1,y+.32,label,va='center',fontsize=9,color='#555e66')
    fig.text(.07,.21,'ΔP / (кресла × LF) × часы плеча ÷ (365 × налёт активного дня × доступность)',fontsize=13,color=TEXT)
    fig.text(.07,.15,'ТО и резерв уже включены в доступность. Существующие 2,7 млн перевозок должны сохраняться.\nОценка не доказывает спрос, прибыль, поставки или наличие свободного парка; типы не взаимозаменяемы.',fontsize=11,color='#555e66')
    fig.text(.07,.065,'Кресла — аналоги текущего флота RW: SSJ100 / Ту-214 / B777. Остальные параметры — сценарии.\nПараметры действующего SSJ100 не подтверждают эксплуатационные показатели SJ-100/ПД-8.',fontsize=10.5,color='#555e66')
    fig.savefig(OUT/'S01_resource_scale.png',dpi=160)
    plt.close(fig)


def baggage():
    fig=plt.figure(figsize=(14,7.3),facecolor='white')
    fig.text(.07,.91,'D02. Сроки покупки багажа на двух страницах',fontsize=23,weight='bold',color=TEXT)
    fig.text(.07,.85,'Проверено на сайте Red Wings 10.11.2026; онлайн-покупка багажа уже существует',fontsize=12,color=TEXT)
    fig.text(.08,.71,'FAQ: как купить багаж',fontsize=16,weight='bold',color=TEXT)
    fig.text(.08,.58,'3 часа',fontsize=37,weight='bold',color=BLUE)
    fig.text(.08,.48,'Рекомендация платить заранее\nза три и более часов до вылета',fontsize=14,color=TEXT,linespacing=1.5)
    fig.text(.55,.71,'Подробная ценовая таблица',fontsize=16,weight='bold',color=TEXT)
    fig.text(.55,.58,'24 часа',fontsize=37,weight='bold',color=RED)
    fig.text(.55,.48,'Граница между двумя уровнями\nопубликованных цен',fontsize=14,color=TEXT,linespacing=1.5)
    fig.text(.08,.32,'Багаж 10–23 кг · внутренний рейс',fontsize=15,weight='bold',color=TEXT)
    fig.text(.08,.24,'Более 24 ч: от 2 700 ₽      Менее 24 ч: от 3 500 ₽',fontsize=17,color=TEXT)
    fig.text(.08,.15,'Исправить согласованность сроков и переход к действующей покупке.\nРазница «от»-цен не гарантирует экономию на каждом рейсе; точную границу подтверждает владелец правил.',fontsize=11,color='#555e66',linespacing=1.5)
    fig.text(.08,.055,'Источники: flyredwings.com/faq/uslugi-na-bortu/dopolnitelnye-uslugi/kak-kupit-dopolnitelnyj-bagazh/\nflyredwings.com/baggage/dopolnitelnyj-bagazh/ · Это наблюдение информации, не подтверждение неверного списания.',fontsize=9.5,color='#555e66')
    fig.savefig(OUT/'D02_deadline_discrepancy.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    market()
    resource()
    baggage()
    print('S01_market_scale.png; S01_resource_scale.png; D02_deadline_discrepancy.png')
