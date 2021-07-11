import tkinter as tk
from tkinter import *

strategies = [
    'EMA Crossover',
]

def loadParameters(frame, strategy):
    pass

root = tk.Tk()
root.title('Cletus The Crypto Trader')

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

# Configure parameter grid
parametersFrame.grid_rowconfigure(0, weight=1)
parametersFrame.grid_rowconfigure(1, weight=1)
parametersFrame.grid_rowconfigure(2, weight=1)
parametersFrame.grid_rowconfigure(3, weight=1)
parametersFrame.grid_rowconfigure(4, weight=1)
parametersFrame.grid_rowconfigure(5, weight=0)

parametersFrame.grid_columnconfigure(0, weight=1)
parametersFrame.grid_columnconfigure(1, weight=1)

# Creating the strategy picker
strategyList = Listbox(listFrame)
strategyList.grid(row=0, column=0, columnspan=2, sticky=NSEW, pady=10)
for strategy in strategies:
    strategyList.insert(END, strategy)

Button(listFrame, padx=20, pady=8, text='Select').grid(row=1, column=0)
Button(listFrame, padx=20, pady=8, text='Rename').grid(row=1, column=1)

# Creating the parameter area
Label(parametersFrame, text='Long Term Period: ').grid(row=0, column=0)
Entry(parametersFrame).grid(row=0, column=1)

Label(parametersFrame, text='Short Term Period: ').grid(row=1, column=0)
Entry(parametersFrame).grid(row=1, column=1)

Label(parametersFrame, text='Smoothing Value: ').grid(row=2, column=0)
Entry(parametersFrame).grid(row=2, column=1)

Button(parametersFrame, padx=20, pady=8, text='Save').grid(row=5, column=0)
Button(parametersFrame, padx=20, pady=8, text='Load').grid(row=5, column=1)

# Creating and placing testing/go live buttons
backtestButton = tk.Button(testButtonsFrame, padx=50, pady=10, text='Backtest')
backtestButton.pack(side='left')

livetestButton = tk.Button(testButtonsFrame, padx=50, pady=10, text='Live Test')
livetestButton.pack(side='right')

liveButton = tk.Button(liveButtonFrame, padx=30, pady=10, text='GO LIVE')
liveButton.pack()

root.mainloop()