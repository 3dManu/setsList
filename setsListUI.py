#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys,os

try:
	# Check import PySide
	from PySide.QtCore import *
	from PySide.QtDeclarative import *
	from PySide.QtGui import *
	from PySide.QtHelp import *
	from PySide.QtMultimedia import *
	from PySide.QtNetwork import *
	from PySide.QtOpenGL import *
	from PySide.QtScript import *
	from PySide.QtScriptTools import *
	from PySide.QtSql import *
	from PySide.QtSvg import *
	from PySide.QtTest import *
	from PySide.QtUiTools import *
	from PySide.QtWebKit import *
	from PySide.QtXml import *
	from PySide.QtXmlPatterns import *
	from PySide.phonon import *
	from shiboken import wrapInstance
except ImportError:
	try:
		# Check import PySide2
		from PySide2.QtCore import *
		from PySide2.QtGui import *
		from PySide2.QtHelp import *
		from PySide2.QtMultimedia import *
		from PySide2.QtNetwork import *
		from PySide2.QtPrintSupport import *
		from PySide2.QtQml import *
		from PySide2.QtQuick import *
		from PySide2.QtQuickWidgets import *
		from PySide2.QtScript import *
		from PySide2.QtSql import *
		from PySide2.QtSvg import *
		from PySide2.QtTest import *
		from PySide2.QtUiTools import *
		from PySide2.QtWebChannel import *
		from PySide2.QtWebKit import *
		from PySide2.QtWebKitWidgets import *
		from PySide2.QtWebSockets import *
		from PySide2.QtWidgets import *
		from PySide2.QtXml import *
		from PySide2.QtXmlPatterns import *
		from shiboken2 import wrapInstance
	except ImportError:
		# Failed import to PySide and PySide2.
		raise ImportError('No module named PySide and PySide2.')
		
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
import re
import maya.cmds as cmds
from itertools import product

from . import setsListWidget
reload(setsListWidget)

class ItemView(QListView):
	def __init__(self,parent=None,title=None,data=None,model=None):
		super(ItemView,self).__init__(parent)
		self.data = data
		self.listModel = model
		self.setAccessibleName(title)
		self.initList()
		
	def initList(self):
		self.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.setModel(self.listModel)
		rows = range(self.listModel.rowCount())
		indexes = self.findRows(self.data)
		hideRows = list(set(rows)-set(indexes))
		for row in hideRows:
			self.setRowHidden(row,True)
	
	def findRows(self,data):
		indexes = []
		if data:
			for node in data:
				item = self.listModel.findItems(node)
				if item:
					index = self.listModel.indexFromItem(item[0])
					indexes.append(index.row())
		return indexes
		
	def removeSelectedItem(self):
		listModel = self.listModel
		selModel = self.selectionModel()
		indexes = selModel.selectedIndexes()
		items =[]		
		for index in indexes:
			items.append(self.listModel.data(index))
		
		setsListWidget.deleteSet(items)
				 
	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Delete:
			self.removeSelectedItem()
			return
			 
		super(ItemView, self).keyPressEvent(event)
	
	def mouseReleaseEvent(self, event):
		QListView.mouseReleaseEvent(self, event)
		selModel = self.selectionModel()
		indexes = selModel.selectedIndexes()
		items = []
		for index in indexes:
			items.append(self.listModel.data(index))
		setsListWidget.selectObjs(items)

class ListField(QDockWidget):
	instID = []
	currentDock = None
	def __init__(self,myNo,parent=None,title=None,data=None,model=None):
		super(ListField,self).__init__(parent)
		self.myNo = myNo
		self.setWindowTitle(title)
		self.listView = ItemView(self,title,data,model)
		self.initDock()
		
	def initDock(self):
		self.setWidget(self.listView)
		self.visibilityChanged[bool].connect(self.selListWidget)
	
	def selListWidget(self,chk):
		sender = self.sender()
		if chk:
			ListField.currentDock = sender
			self.listView.setFocus()
	
	def closeEvent(self, event):
		ListField.instID.remove(self.myNo)
	
class listViewModel(QStandardItemModel):
	def setData(self,index,value,role):
		if role == Qt.EditRole:
			item = self.itemFromIndex(index).text()
			value = setsListWidget.renameItem(item,value)
		return QStandardItemModel.setData(self, index, value, role)
	
	def setDataWithoutRename(self,index,value,role):
		return QStandardItemModel.setData(self, index, value, role)
		
class editSetName(QWidget):
	def __init__(self,setName, parent=None):
		super(editSetName, self).__init__(parent)
		self.setWindowFlags(Qt.Window)
		self.setWindowTitle('renameSet')
		self.parent = parent
		self.setName = setName
		
		self.initUI()
	
	def initUI(self):
		self.lineEdit = QLineEdit(self.setName)
		
		self.aplyBtn = QPushButton('Apply')
		self.aplyBtn.clicked.connect(self.applySetName)
	
		self.layout = QVBoxLayout()
		
		self.layout.addWidget(self.lineEdit)
		self.layout.addWidget(self.aplyBtn)
		
		self.setLayout(self.layout)
 
	#----------------------------------------
	## UI要素のステータスやら値やらプリントする
	def applySetName(self):
		self.close()
		self.parent.editWindowTitle(self.lineEdit.text())
		
class SetsListUI(QWidget):
	def __init__(self,parent=None):
		ptr = OpenMayaUI.MQtUtil.mainWindow()
		parent = wrapInstance(long(ptr),QWidget)
		super(SetsListUI, self).__init__(parent)
		self.setWindowFlags(Qt.Window)
		self.resize(200,300)
		self.setWindowTitle('SetsList')
		self.initUI()
		
	def initUI(self):
		self.cnt = 0
		self.dockUI = []
		self.callbackID = OpenMaya.MNodeMessage.addNameChangedCallback(OpenMaya.MObject(), self.nameIsChanged)#リネーム時に処理が走る
		self.listModel = listViewModel()
		self.jobNo = [None,None,None]
		
		#button
		self.hilgtBtn = QToolButton(self)
		self.allReBtn = QToolButton(self)
		self.newSetBtn = QToolButton(self)
		self.delSetBtn = QToolButton(self)
		self.addSetBtn = QToolButton(self)
		self.remSetBtn = QToolButton(self)
		
		self.reNameBtn = QPushButton(self)
		
		#topButton---------
		self.hilgtBtn.setText("Hi")
		self.allReBtn.setText("Re")
		self.newSetBtn.setText("New")
		self.delSetBtn.setText("Del")
		self.addSetBtn.setText("Add")
		self.remSetBtn.setText("Rem")
		self.reNameBtn.setText("renameSet")
		#-------------------
		
		self.hilgtBtn.setCheckable(True)
		self.hilgtBtn.toggled.connect(self.hiliteList)
		self.hilgtBtn.setChecked(True)
		self.allReBtn.clicked.connect(self.reloadAllList)
		
		self.newSetBtn.clicked.connect(self.newSet)
		self.delSetBtn.clicked.connect(self.delSet)
		self.addSetBtn.clicked.connect(self.addSet)
		self.remSetBtn.clicked.connect(self.remSet)
		
		self.reNameBtn.clicked.connect(self.renameSetWindow)
		
		#botButton---------
		self.addItemBtn = QPushButton("Add",self)
		self.remItemBtn = QPushButton("Remove",self)
		self.selItemBtn = QPushButton("Select All",self)
		self.clrItemBtn = QPushButton("Clear",self)
		#-------------------
		
		self.addItemBtn.clicked.connect(self.addItem)
		self.remItemBtn.clicked.connect(self.removeItem)
		self.selItemBtn.clicked.connect(self.selectAllItem)
		self.clrItemBtn.clicked.connect(self.clearItem)
		
		self.objRadio = QRadioButton("objectSets",self)
		self.shdRadio = QRadioButton("shadingGroup",self)
		self.objRadio.setChecked(True)
		self.objRadio.clicked.connect(self.reloadAllList)
		self.shdRadio.clicked.connect(self.reloadAllList)
		
		self.tabMain = QMainWindow(self)
		self.tabMain.setWindowFlags(Qt.Widget)
		self.tabMain.setTabPosition(Qt.TopDockWidgetArea,QTabWidget.North)
		
		#design
		self.addItemBtn.setFixedWidth(60)
		self.remItemBtn.setFixedWidth(60)
		self.selItemBtn.setFixedWidth(60)
		self.clrItemBtn.setFixedWidth(60)
		
		self.objRadio.setFixedWidth(70)
		self.shdRadio.setFixedWidth(90)
		
		#layout
		self.vLay = QVBoxLayout()
		self.hTopLay = QHBoxLayout()
		self.hTabEditLay = QHBoxLayout()
		self.hTabLay = QHBoxLayout()
		self.hBotLay = QHBoxLayout()
		
		self.hTopLay.addWidget(self.hilgtBtn)
		self.hTopLay.addWidget(self.allReBtn)
		self.hTopLay.addWidget(self.objRadio,1,(Qt.AlignRight|Qt.AlignVCenter))
		self.hTopLay.addWidget(self.shdRadio,0,(Qt.AlignRight|Qt.AlignVCenter))
		
		self.hTabEditLay.addWidget(self.reNameBtn)
		self.hTabEditLay.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
		
		self.hTabEditLay.addWidget(self.newSetBtn)
		self.hTabEditLay.addWidget(self.delSetBtn)
		self.hTabEditLay.addWidget(self.addSetBtn)
		self.hTabEditLay.addWidget(self.remSetBtn)
		self.hTabEditLay.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
		self.hTabEditLay.setSpacing(15)
		
		self.hTabLay.addWidget(self.tabMain)
		
		self.hBotLay.addWidget(self.addItemBtn)
		self.hBotLay.addWidget(self.remItemBtn)
		self.hBotLay.addWidget(self.selItemBtn)
		self.hBotLay.addWidget(self.clrItemBtn)
		
		self.vLay.addLayout(self.hTopLay)
		self.vLay.addLayout(self.hTabEditLay)
		self.vLay.addLayout(self.hTabLay)
		self.vLay.addLayout(self.hBotLay)
		
		self.setLayout(self.vLay)
		#-----
		
		self.buildTabs()
		self.listModel.sort(0,Qt.AscendingOrder)
		self.createScriptJobs()
		self.show()
	
	def closeEvent(self, e):
		self.deleteScriptJobs()
		OpenMaya.MNodeMessage.removeCallback(self.callbackID)
	
	def addDocks(self,title,data,fstDock=None):
		dock = ListField(self.cnt,self,title,data,self.listModel)
		ListField.instID.append(self.cnt)
		self.tabMain.addDockWidget(Qt.TopDockWidgetArea,dock)
		self.cnt+=1
		if fstDock != None:
			self.tabMain.tabifyDockWidget(fstDock,dock)
		return dock
	
	def addTab(self,tabName,list):
		self.appendItemModel(list)
		instID = ListField.instID
		if len(instID)>0:
			self.dockUI.append(self.addDocks(tabName,list,self.dockUI[instID[0]]))
			self.dockUI[-1].listView.setSelectionModel(self.dockUI[0].listView.selectionModel())
		else:
			self.dockUI.append(self.addDocks(tabName,list))
	
	def buildTabs(self):
		tabNames = setsListWidget.setsExtract(self.objRadio.isChecked())
		for tabName in tabNames:
			list = setsListWidget.objExtract(tabName)
			self.addTab(tabName,list)
		
	def createScriptJobs(self):
		self.jobNo[1] = setsListWidget.addScriptJobs(self.deletedObject,"delete")
		self.jobNo[2] = setsListWidget.addScriptJobs(self.changedRenderLayer,"changerl")
	
	def deleteScriptJobs(self):
		setsListWidget.delScriptJobs(self.jobNo[0])
		setsListWidget.delScriptJobs(self.jobNo[1])
		setsListWidget.delScriptJobs(self.jobNo[2])

	def nameIsChanged(self,node, prevName, clientData):
		listModel = self.listModel
		newName = OpenMaya.MFnDependencyNode(node).name()
		obj = prevName
		item = self.listModel.findItems(obj)
		if item:
			index = self.listModel.indexFromItem(item[0])
			listModel.setDataWithoutRename(index,newName,Qt.EditRole)
	
	def selectionLists(self):
		start = time.time()
		currentDock = ListField.currentDock 
		if currentDock != None:
			listView = currentDock.listView
			listModel = self.listModel
			objs = setsListWidget.selectLists()
			selModel = listView.selectionModel()
			selModel.clear()
			for obj in objs:
				item = listModel.findItems(obj)
				if item:
					index = listModel.indexFromItem(item[0])
					selModel.select(index,QItemSelectionModel.Select)
		elapsed_time = time.time() - start
		print ("elapsed_time:{0}".format(elapsed_time) + "[sec]")
	
	def deletedObject(self):
		listA = []
		listB = []
		li = []
		tabNames = setsListWidget.setsExtract(self.objRadio.isChecked())
		for tabName in tabNames:
			li.extend(setsListWidget.objExtract(tabName))
		
		listA = list(set(li))
		
		listModel = self.listModel
		indexes = listModel.persistentIndexList()
		items = []
		for index in indexes:
			listB.append(self.listModel.data(index))
				
		set_ab = set(listB) - set(listA)
		deleteObjs = list(set_ab)
		
		for obj in deleteObjs:
			item = listModel.findItems(obj)
			listModel.removeRow(item[0].row())
			
	def changedRenderLayer(self):
		if self.shdRadio.isChecked():
			self.reloadAllList()
			
	#====================================================
	#=============bottom Button Command==================
	def hiliteList(self,chk):
		if chk:
			self.jobNo[0] = setsListWidget.addScriptJobs(self.selectionLists,"selection")
		else:
			setsListWidget.delScriptJobs(self.jobNo[0])
			
	def reloadAllList(self):
		for dock in self.dockUI:
			dock.close()
		self.cnt = 0
		self.dockUI = []
		
		self.buildTabs()
	
	def renameSetWindow(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		editWindow = editSetName(setName,self)
		editWindow.show()
	
	def editWindowTitle(self,name):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		newName = setsListWidget.renameItem(setName,name)
		listView.setAccessibleName(newName)
		listView.parentWidget().setWindowTitle(newName)
		
	#------------------------------------------------------
	
	def newSet(self):
		tabName = "setList" + str(self.cnt)
		setsListWidget.createSet(tabName)
		self.addTab(tabName,None)
	
	def addSet(self):
		tabNames = setsListWidget.addSetTab()
		setNames =[]
		for dock in self.dockUI:
			setNames.append(dock.listView.accessibleName())
		if not tabNames:
			return
		for tabName in tabNames:
			if tabName not in setNames:
				list = setsListWidget.objExtract(tabName)
				self.addTab(tabName,list)
				
	def delSet(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		setsListWidget.deleteSet(setName)
		dock = listView.parentWidget()
		dock.close()
		self.dockUI.remove(dock)
	
	def remSet(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		setsListWidget.removeSet(setName)
		dock = listView.parentWidget()
		dock.close()
		self.dockUI.remove(dock)
		
	#------------------------------------------------------
	
	def addItem(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		data = setsListWidget.addObj(setName)
		curNo = listView.parentWidget().myNo
		#すでにmodelにあるものだった場合リストにshowする
		chks = self.appendItemModel(data,curNo)
		for chk in chks:
			if chk:
				rows = listView.findRows(data)
				for row in rows:
					listView.setRowHidden(row,False)
	
	def removeItem(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		model = listView.model()
		selModel = listView.selectionModel()
		items = []
		
		indexes = selModel.selectedIndexes()
		for index in indexes:
			items.append(model.data(index))
			listView.setRowHidden(index.row(),True)
			
		setsListWidget.removeObj(setName,items)
		
	def selectAllItem(self):
		listView = self.tabMain.focusWidget()
		curNo = listView.parentWidget().myNo
		setName = listView.accessibleName()
		objs = setsListWidget.selectAll(setName)
		listView.selectAll()
				
	def clearItem(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		setsListWidget.clearSet(setName)
		listModel = self.listModel
		row = listModel.rowCount()
		for i in range(row):
			listView.setRowHidden(i,True)
		
	#====================================================
	#====================================================
	#addItemをしたときに全てのリストに表示されるので表示しなくて良いリストを判別してhideをかける
	
	def appendItemModel(self,data,curID = None):
		listModel = self.listModel
		instID = ListField.instID
		chk = []
		if data:
			for node in data:
				item = listModel.findItems(node)
				if not item:
					listModel.appendRow(QStandardItem(node))
					for id in instID:
						if id != curID:
							row = listModel.rowCount()
							self.dockUI[id].listView.setRowHidden((row-1),True)
					chk.append(False)
				else:
					chk.append(True)
		return chk
		
def main():
	app = QApplication.instance()
	ui = SetsListUI()
	sys.exit()
	app.exec_()

if __name__ == "__main__":
	main()