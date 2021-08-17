#  Version 0.1 - Model T
#  Author: Reilly Schultz
#  Date: August 16th, 2021

import config
import json
import tkinter as tk
from tkinter import *
import threading
import LiveTestingEMA

strategies = {}
with open('strategies.json') as file:
    strategies = json.load(file)
parameterEntries = {}

def loadParameters(strategy):
    # Make and fill a row for each parameter + 1 row for save and load
    for n, param in enumerate(strategy):
        parametersFrame.grid_rowconfigure(n, weight=1)
        rowCount = n
    parametersFrame.grid_rowconfigure(rowCount+1, weight=0)

    parametersFrame.grid_columnconfigure(0, weight=1)
    parametersFrame.grid_columnconfigure(1, weight=1)

    for n, param in enumerate(strategy):
        Label(parametersFrame, text=param).grid(row=n, column=0)
        if isinstance(strategy[param], int):
            numEntry = Spinbox(parametersFrame, from_=0, to=2000, width=5)
            numEntry.grid(row=n, column=1)
            numEntry.delete(0, END)
            numEntry.insert(0, strategy[param])
            parameterEntries[param] = numEntry

        else:
            stringEntry = Entry(parametersFrame)
            stringEntry.grid(row=n, column=1)
            stringEntry.insert(0, strategy[param])
            parameterEntries[param] = stringEntry

def saveNewStrategy():
    # Making a new window to receive name for the user's strategy they want to save
    nameWin = Toplevel()
    nameWin.title('Cletus The Crypto Connoisseur - Name Your Strategy')
    nameWin.minsize(250, 60)
    nameWin.maxsize(250, 60)

    # Centers the window
    w=250
    h=60
    screen_width = nameWin.winfo_screenwidth()
    screen_height = nameWin.winfo_screenheight()
    x = (screen_width/2) - (w/2)
    y = (screen_height/2) - (h/2)
    nameWin.geometry('%dx%d+%d+%d' % (w, h, x, y))

    nameWin.grid_rowconfigure(0, weight=1)
    nameWin.grid_rowconfigure(1, weight=1)

    nameWin.grid_columnconfigure(0, weight=1)
    nameWin.grid_columnconfigure(1, weight=1)
    
    # Create input
    Label(nameWin, text='Enter Strategy Name:').grid(row=0, column=0)

    strategyName = tk.StringVar(nameWin)

    nameEntry = Entry(nameWin, textvariable=strategyName)
    nameEntry.grid(row=0, column=1)

    finishEntry = Button(nameWin, text='Done', command=lambda: saveParameters(nameWin, strategyName.get()))
    finishEntry.grid(row=1, column=0, columnspan=2)

# Saves the current filled parameters in the GUI to the strategies dict
def saveParameters(saveNameWindow, strategyName):
    saveNameWindow.withdraw()

    newStrategy = {}

    for param in parameterEntries:
        try:
            newStrategy[param] = int(parameterEntries[param].get())
        except:
            newStrategy[param] = parameterEntries[param].get()

    strategies[strategyName] = newStrategy
    with open('strategies.json', 'w+') as file:
        json.dump(strategies, file)

    strategyList.insert(END, strategyName)

def deleteStrategy(strategyName):
    if strategyName == 'EMA Crossover Default':
        return
    del strategies[strategyName]
    strategyList.delete(strategyList.curselection())

    with open('strategies.json', 'w+') as file:
        json.dump(strategies, file)

def renameStrategy(strategyName):
    if strategyName == 'EMA Crossover Default':
        return
    saveNewStrategy()
    deleteStrategy(strategyName)

# Returns the currently selected line in a Listbox
def getListSelection(list):
    currentSelected = list.curselection()
    selectedStrategy = list.get(currentSelected)
    return selectedStrategy

def liveTest(strategy):
    print('Live Testing')
    liveTestThread = threading.Thread(target=lambda: LiveTestingEMA.runBot(strategy))
    liveTestThread.start()

root = tk.Tk()
root.title('Cletus The Crypto Connoisseur')

# Setting the position of the window to the center of the screen
w = 750
h = 600

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width/2) - (w/2)
y = (screen_height/2) - (h/2)

root.geometry('%dx%d+%d+%d' % (w, h, x, y))

# Configure root grid
root.grid_rowconfigure(0, weight=3)
root.grid_rowconfigure(1, weight=0)

root.grid_columnconfigure(0, weight=2)
root.grid_columnconfigure(1, weight=3)

# Creating frames
listFrame = Frame(root, bg='#FFF0C1', bd=20)
parametersFrame = Frame(root, bg='#D2E2FB', bd=20)
testButtonsFrame = Frame(root, bg='#CCE4CA', bd=30)
liveButtonFrame = Frame(root, bg='#00E4CA', bd=30)

# Organize frames
listFrame.grid(row=0, column=0, sticky=NSEW)
parametersFrame.grid(row=0, column=1, sticky=NSEW)
testButtonsFrame.grid(row=1, column=0, sticky=NSEW)
liveButtonFrame.grid(row=1, column=1, sticky=NSEW)

# Configure list grid
listFrame.grid_rowconfigure(0, weight=1)
listFrame.grid_rowconfigure(1, weight=0)

listFrame.grid_columnconfigure(0, weight=1)
listFrame.grid_columnconfigure(1, weight=1)
listFrame.grid_columnconfigure(2, weight=0)

# Creating the strategy picker
strategyListScrollbar = Scrollbar(listFrame)
strategyListScrollbar.grid(row=0, column=2, sticky=NSEW, pady=10)

strategyList = Listbox(listFrame, selectmode=SINGLE, yscrollcommand=strategyListScrollbar.set)
strategyList.grid(row=0, column=0, columnspan=2, sticky=NSEW, pady=10)
for n, strategy in enumerate(strategies):
    strategyList.insert(n, strategy)

Button(listFrame, padx=20, pady=8, text='Rename', command=lambda: renameStrategy(getListSelection(strategyList))).grid(row=1, column=0)
Button(listFrame, padx=20, pady=8, text='Delete', command=lambda: deleteStrategy(getListSelection(strategyList))).grid(row=1, column=1)

# Configure parameter grid
loadParameters(strategies['EMA Crossover Default'])
column, row = parametersFrame.grid_size()
Button(parametersFrame, padx=20, pady=8, text='Save', command=lambda: saveNewStrategy()).grid(row=row, column=0)
Button(parametersFrame, padx=20, pady=8, text='Load', command=lambda: loadParameters(strategies[getListSelection(strategyList)])).grid(row=row, column=1)

# Creating and placing testing/go live buttons
backtestButton = tk.Button(testButtonsFrame, padx=50, pady=10, text='Backtest')
backtestButton.pack(side='left')

livetestButton = tk.Button(testButtonsFrame, padx=50, pady=10, text='Live Test', command=lambda: liveTest(strategies[getListSelection(strategyList)]))
livetestButton.pack(side='right')

liveButton = tk.Button(liveButtonFrame, padx=30, pady=10, text='GO LIVE')
liveButton.pack()

root.mainloop()