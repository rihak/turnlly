from flask import Flask, request
import telepot
import urllib3
import datetime
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

import cfg


# TurnLLY Version
VERSION = '3.2.0'

# Emoji
class ICONS:
    BLUE = '🔵'
    RED = '🔴'
    YELLOW = '🟡'
    GREEN = '🟢'
    PURPLE = '🟣'
    NONE = '⚫️'
    MORNING = '🏞'
    AFTERNOON = '🌆'
    NIGHT = '🌃'
    HOLYDAY = '🐳'
    VERTICAL = '|'



################################################################################
############################## DateTime Utilities ##############################
################################################################################

WEEK = [
    'Lunedì',
    'Martedì',
    'Mercoledì',
    'Giovedì',
    'Venerdì',
    'Sabato',
    'Domenica',
]

YEAR = [
    '',
    'Gennaio',
    'Febbraio',
    'Marzo',
    'Aprile',
    'Maggio',
    'Giugno',
    'Luglio',
    'Agosto',
    'Settembre',
    'Ottobre',
    'Novembre',
    'Dicembre',
]


# Get the Current Italian DateTime object
def now() -> datetime.datetime:
    utcOffset = 1
    timestamp = datetime.datetime.now()
    switchMar = datetime.datetime(timestamp.year, 3, 31 - (datetime.datetime(timestamp.year, 3, 31).weekday() + 1) % 7, 3, 0, 0)
    switchOct = datetime.datetime(timestamp.year, 10, 31 - (datetime.datetime(timestamp.year, 10, 31).weekday() + 1) % 7, 2, 0, 0)
    if switchMar < timestamp < switchOct:
        utcOffset += 1
    return timestamp + datetime.timedelta(hours=utcOffset)

# Get the length (in days) of a specific month
def monthLength(month: int, year: int) -> int:
    if month < 1 or month > 12:
        return 0
    if month != 2:
        return [31, 0, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28


def isHoliday(date: datetime.datetime) -> bool:
    a = date.year % 19
    b = date.year // 100
    c = date.year % 100
    d = (19*a + b - b//4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2*(b % 4) + 2*(c // 4) - d - (c % 4)) % 7
    f = d + e - 7*((a + 11*d + 22*e)//451) + 114
    easterMonth = f // 31
    easterDay = f % 31 + 1
    easterDate = datetime.date(date.year, easterMonth, easterDay)
    holidays = [
        "01-01", # Capodanno
        "01-06", # Epifania
        easterDate.strftime("%m-%d"), # Pasqua
        (easterDate + datetime.timedelta(days=1)).strftime("%m-%d"), # Lunedì dell'Angelo
        "04-25", # Festa della Liberazione
        "05-01", # Festa del Lavoro
        "06-02", # Festa della Repubblica
        "08-15", # Assunzione di Maria
        "11-01", # Ognissanti
        "12-08", # Immacolata Concezione
        "12-25", # Natale
        "12-26", # Santo Stefano
    ]
    return date.strftime("%m-%d") in holidays



################################################################################
################################### Parsers ####################################
################################################################################

def parseDay(day: str) -> datetime.datetime:
    for i, option in enumerate(['i', 'ieri', 'o', 'oggi', 'd', 'domani']):
        if day == option:
            return now() + datetime.timedelta(days=i // 2 - 1)
    date = day.split('.')
    resultDay = now()
    try:
        resultDay = resultDay.replace(day=int(date[0]))
        resultDay = resultDay.replace(month=int(date[1]))
        resultDay = resultDay.replace(year=int(f"{'20' if len(date[2]) == 2 else ''}{date[2]}"))
    except:
        pass
    return resultDay

def parseMonth(month: str) -> datetime.datetime:
    date = month.split('.')
    resultDay = now().replace(day=1)
    try:
        resultDay = resultDay.replace(month=int(date[0]))
        resultDay = resultDay.replace(year=int(f"{'20' if len(date[1]) == 2 else ''}{date[1]}"))
    except:
        pass
    return resultDay



################################################################################
################################### TurnLLY ####################################
################################################################################

def shift(daySeconds: int) -> int:
    for turn, turnLimitSeconds in enumerate([28800, 57600, 86400]):
        if daySeconds < turnLimitSeconds:
            return turn

def team(timestamp: datetime.datetime) -> str:
    cycleSeconds = int((timestamp - datetime.datetime(2018, 9, 2, 5, 30, 0)).total_seconds()) % 864000
    daySeconds = cycleSeconds % 86400
    shiftType = shift(daySeconds)
    dayType = int(cycleSeconds / 172800)
    return [ICONS.BLUE, ICONS.GREEN, ICONS.YELLOW, ICONS.RED, ICONS.PURPLE][(5 - dayType + shiftType) % 5]



################################################################################
#################################### Views #####################################
################################################################################

def turnView(timestamp: datetime.datetime) -> str:
    if timestamp == 0:
        return "ERRORE: Formato parametro DATA non corretto. Per informazioni sull'utilizzo dei parametri, utilizzare /h ."
    return f" {WEEK[timestamp.weekday()]} {str(timestamp.day)} {YEAR[timestamp.month]} {str(timestamp.year)}{'' if not isHoliday(timestamp) else ' ' + ICONS.HOLYDAY}:\nOre {str(timestamp.hour):0>2}:{str(timestamp.minute):0>2}\n\n{team(timestamp)}"

def dayView(day: datetime.datetime) -> str:
    if day == 0:
        return "ERRORE: Formato parametro DATA non corretto. Per informazioni sull'utilizzo dei parametri, utilizzare /h ."
    return f" {WEEK[day.weekday()]} {str(day.day)} {YEAR[day.month]} {str(day.year)}{'' if not isHoliday(day) else ' ' + ICONS.HOLYDAY}:\n\n{ICONS.MORNING}: {team(day.replace(hour = 7))}\n{ICONS.AFTERNOON}: {team(day.replace(hour = 15))}\n{ICONS.NIGHT}: {team(day.replace(hour = 23))}\n"

def scheduleView(startDay: datetime.datetime, daysToShow: str) -> str:
    try:
        daysToShow = int(daysToShow)
    except:
        return "ERRORE: Formato parametro GIORNI non corretto. Per informazioni sull'utilizzo dei parametri, utilizzare /h ."
    if daysToShow > 90:
        return "ERRORE: Il parametro GIORNI non può essere maggiore di 90 per questo comando."
    result = f'        {ICONS.MORNING}{ICONS.AFTERNOON}{ICONS.NIGHT}\n'
    for i in range(daysToShow):
        shiftDate = startDay + datetime.timedelta(days = i)
        if shiftDate.day == 1 or i == 0:
            result += f'\n {YEAR[shiftDate.month]} {str(shiftDate.year)}\n'
        result += f"{WEEK[shiftDate.weekday()][:3]} {str(shiftDate.day):0>2}: {team(shiftDate.replace(hour = 7))}{team(shiftDate.replace(hour = 15))}{team(shiftDate.replace(hour = 23))}{'' if not isHoliday(shiftDate) else ' ' + ICONS.HOLYDAY}\n"
    result += '.'
    return result

def monthView(month: datetime.datetime) -> str:
    if month == 0:
        return "ERRORE: Formato parametro DATA non corretto. Per informazioni sull'utilizzo dei parametri, utilizzare /h ."

    result = f'        {ICONS.MORNING}{ICONS.AFTERNOON}{ICONS.NIGHT}\n\n {YEAR[month.month]} {str(month.year)}\n'
    workDays = 0
    workDaysTeams = { ICONS.BLUE: 0, ICONS.YELLOW: 0, ICONS.RED: 0, ICONS.PURPLE: 0, ICONS.GREEN: 0, }

    for i in range(monthLength(month.month, month.year)):
        shiftDate = month + datetime.timedelta(days = i)
        shiftDateIsHoliday = isHoliday(shiftDate)
        workDays += shiftDate.weekday() < 5 and not shiftDateIsHoliday
        morning = team(shiftDate.replace(hour = 7))
        workDaysTeams[morning] += 1 if not shiftDateIsHoliday else 0
        afternoon = team(shiftDate.replace(hour = 15))
        workDaysTeams[afternoon] += 1 if not shiftDateIsHoliday else 0
        night =  team(shiftDate.replace(hour = 23))
        workDaysTeams[night] += 1 if not shiftDateIsHoliday else 0
        result += f"{WEEK[shiftDate.weekday()][:3]} {str(shiftDate.day):0>2}: {morning}{afternoon}{night}{'' if not shiftDateIsHoliday else ' ' + ICONS.HOLYDAY}\n"

    result += f'\nLavorativi:\n{workDays}({workDays * 8}h)\n\n'

    for t in workDaysTeams.keys():
        result += f'{t}: {workDaysTeams[t]} ({workDaysTeams[t] * 8}h){workDays - workDaysTeams[t]:+>2}\n'
    result += '.'
    return result



telepot.api._pools = { 'default': urllib3.ProxyManager(proxy_url=cfg.proxyUrl, num_pools=3, maxsize=10, retries=False, timeout=30), }
telepot.api._onetime_pool_spec = (urllib3.ProxyManager, dict(proxy_url=cfg.proxyUrl, num_pools=1, maxsize=1, retries=False, timeout=30))

bot = telepot.Bot(cfg.botToken)
bot.setWebhook(cfg.webhookUrl, max_connections=1)



################################################################################
################################### Handles ####################################
################################################################################

app = Flask(__name__)
@app.route(f"/{cfg.webhookGuid}", methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if "message" in update:
        try:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            if text.lower() == "/start" or text.lower() == "/help" or text.lower() == "/h":
                bot.sendMessage(chat_id, f"TurnLLY ({VERSION}) ti da il Benvenuto.\n\nPARAMETRI:\n\n`GIORNO` : Una specifica data. Inserire il parametro nella forma `GG.MM.AAAA`. Se si vuole specificare una data compresa nell\'anno corrente, inserire il parametro nella forma `GG.MM`. Se si vuole specificare una data compresa nel mese corrente, inserire il parametro nella forma `GG`. Specificare il parametro come: `ieri`(oppure `i`), `oggi`(oppure `o`) o `domani`(oppure `d`) se si desidera specificare rispettivamente la data di ieri, oggi o domani.\n\n`MESE` : Uno specifico mese. Inserire il parametro nella forma `MM.AAAA`. Se si vuole specificare un mese compreso nell\'anno corrente, inserire il paraetro nella forma `MM`.\n\n`GIORNI` : Un numero/ammontare di giorni. Inserire il parametro specificando un numero intero che rappresenta un qantitativo di giorni.\n\n\nCOMANDI:\n\n/adesso : Mostra le squadre a turno nel momento in cui si esegue il comando. Comandi brevi: /n, /ora\n\n/data `GIORNO` : Mostra le squadre a turno per la data specificata attraverso il parametro `GIORNO`. I parametri possono essere omessi: in tal caso assumeranno i valori di default `GIORNO`=`oggi`. Comando breve: /d.\n\n/schedule `GIORNO` `GIORNI` : Mostra la tabella dei turni di lunghezza specificata con il parametro `GIORNI` che comincia dalla data specificata con il parametro `GIORNO`. I parametri possono essere omessi: in tal caso assumeranno i valori di default `GIORNO`=`oggi`, `GIORNI`= `12`. Comando breve: /s.\n\n/mese `MESE` : Mostra la tabella dei turni del mese specificato attraverso il parametro `MESE`. Mostra inoltre il numero di giorni lavorativi di tale mese, e un breve riassunto dei giorni lavorati e dei rientri di ciascuna squadra. I parametri possono essere omessi: in tal caso assumeranno i valori di default `MESE`=`corrente`. Comando breve: /m.\n\n\nLEGENDA ICONE:\n\n{ICONS.BLUE}: Squadra Blu\n{ICONS.RED}: Squadra Rossa\n{ICONS.YELLOW}: Squadra Gialla\n{ICONS.GREEN}: Squadra Verde\n{ICONS.PURPLE}: Squadra Viola\n{ICONS.NONE}: Nessuna Squadra\n{ICONS.MORNING}: Turno Mattutino\n{ICONS.AFTERNOON}: Turno Pomeridiano\n{ICONS.NIGHT}: Turno Notturno\n{ICONS.HOLYDAY}: Giorno Festivo", parse_mode="Markdown")
                #bot.sendMessage(chat_id, 'Inoltre TurnLLY offre la possibilità di utilizzare rapidamente dei comandi predefiniti senza parametri con la tastiera personalizzata:', reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="/adesso"), KeyboardButton(text="/data")], [KeyboardButton(text="/schedule"), KeyboardButton(text="/mese")]]))

            elif text.lower() == "/ora" or text.lower() == "/adesso" or text.lower() == "/n":
                bot.sendMessage(chat_id, "```{}```".format(turnView(now())), parse_mode="Markdown")

            elif text.lower() == "/schedule" or text.lower() == "/s":
                bot.sendMessage(chat_id, "```{}```".format(scheduleView(now(), 12)), parse_mode="Markdown")

            elif (text.split()[0].lower() == "/schedule" or text.split()[0].lower() == "/s") and len(text.split()) == 3:
                bot.sendMessage(chat_id, "```{}```".format(scheduleView(parseDay(text.split()[1].lower()), text.split()[2])), parse_mode="Markdown")

            elif text.lower() == "/data" or text.lower() == "/d":
                bot.sendMessage(chat_id, "```{}```".format(dayView(now())), parse_mode="Markdown")

            elif text.split()[0].lower() == "/data" or text.split()[0].lower() == "/d":
                bot.sendMessage(chat_id, "```{}```".format(dayView(parseDay(text.split()[1].lower()))), parse_mode="Markdown")

            elif text.lower() == "/mese" or text.lower() == "/m":
                bot.sendMessage(chat_id, "```{}```".format(monthView(now().replace(day=1))), parse_mode="Markdown")

            elif text.split()[0].lower() == "/mese" or text.split()[0].lower() == "/m":
                bot.sendMessage(chat_id, "```{}```".format(monthView(parseMonth(text.split()[1].lower()))), parse_mode="Markdown")

        except KeyError:
            pass

    return "OK"





