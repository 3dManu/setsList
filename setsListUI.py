#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys,os

try:
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
		items = self.selectionListItems()
		setsListWidget.deleteSet(items)
				 
	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Delete:
			self.removeSelectedItem()
			return
			 
		super(ItemView, self).keyPressEvent(event)
	
	def mouseReleaseEvent(self, event):
		QListView.mouseReleaseEvent(self, event)
		items = self.selectionListItems()
		setsListWidget.selectObjs(items)
		
	def selectionListItems(self):
		selModel = self.selectionModel()
		indexes = selModel.selectedIndexes()
		items = []
		for index in indexes:
			items.append(self.listModel.data(index))
		return items
		

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
		if not chk:
			return
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
		self.callbackIDs = {}
		self.listModel = listViewModel()
		self.jobNo = [None,None,None]
		
		self.hilgtBtn = QToolButton(self)
		self.allReBtn = QToolButton(self)
		self.newSetBtn = QToolButton(self)
		self.delSetBtn = QToolButton(self)
		self.addSetBtn = QToolButton(self)
		self.remSetBtn = QToolButton(self)
		
		self.reNameBtn = QPushButton(self)
		
		self.hilgtBtn.setText("Hi")
		self.allReBtn.setText("Re")
		self.newSetBtn.setText("New")
		self.delSetBtn.setText("Del")
		self.addSetBtn.setText("Add")
		self.remSetBtn.setText("Rem")
		self.reNameBtn.setText("renameSet")
		
		self.hilgtBtn.setCheckable(True)
		self.hilgtBtn.toggled.connect(self.hiliteList)
		self.hilgtBtn.setChecked(True)
		self.allReBtn.clicked.connect(self.reloadAllList)
		
		self.newSetBtn.clicked.connect(self.newSet)
		self.delSetBtn.clicked.connect(self.delSet)
		self.addSetBtn.clicked.connect(self.addSet)
		self.remSetBtn.clicked.connect(self.remSet)
		
		self.reNameBtn.clicked.connect(self.renameSetWindow)
		
		self.addItemBtn = QPushButton("Add",self)
		self.remItemBtn = QPushButton("Remove",self)
		self.selItemBtn = QPushButton("Select All",self)
		self.clrItemBtn = QPushButton("Clear",self)
		
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
		
		self.addItemBtn.setFixedWidth(60)
		self.remItemBtn.setFixedWidth(60)
		self.selItemBtn.setFixedWidth(60)
		self.clrItemBtn.setFixedWidth(60)
		
		self.objRadio.setFixedWidth(70)
		self.shdRadio.setFixedWidth(90)
		
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
		
		self.buildTabs()
		self.listModel.sort(0,Qt.AscendingOrder)
		self.show()
	
	def closeEvent(self, e):
		for no in self.jobNo:
			try:
				setsListWidget.delScriptJobs(no)
			except:
				pass
		for id in self.callbackIDs.items():
			try:
				OpenMaya.MMessage.removeCallback(id[1])
			except:
				pass
	
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
		self.callbackIDs["__callBack.NameChenged"] = OpenMaya.MNodeMessage.addNameChangedCallback(OpenMaya.MObject(), self.nameIsChanged)
		self.callbackIDs["__callBack.Connection"] = OpenMaya.MDGMessage.addConnectionCallback(self.checkConnectedPlug)
		
		tabNames = setsListWidget.setsExtract(self.objRadio.isChecked())
		for tabName in tabNames:
			list = setsListWidget.objExtract(tabName)
			self.addTab(tabName,list)
			for item in list:
				meshName = item.split(".")
				if len(meshName)<=1:
					continue
				meshName = meshName[0]
				self.callbackIDs["_%s.%s"%(meshName,tabName)] = self.setAttributeCallback(meshName,tabName)

	def nameIsChanged(self,node, prevName, clientData):
		listModel = self.listModel
		newName = OpenMaya.MFnDependencyNode(node).name()
		obj = prevName
		item = self.listModel.findItems(obj)
		if item:
			index = self.listModel.indexFromItem(item[0])
			listModel.setDataWithoutRename(index,newName,Qt.EditRole)
	
	def selectionLists(self):
		currentDock = ListField.currentDock 
		if currentDock == None:
			return
		listView = currentDock.listView
		listModel = self.listModel
		objs = setsListWidget.selectLists()
		selModel = listView.selectionModel()
		selModel.clear()
		for obj in objs:
			item = listModel.findItems(obj)
			if not item:
				continue
			index = listModel.indexFromItem(item[0])
			selModel.select(index,QItemSelectionModel.Select)
	
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
			
	def checkConnectedPlug(self,srcPlug,destPlug,made,clintData):
		srcName = OpenMaya.MFnDependencyNode(srcPlug.node()).name()
		destName = OpenMaya.MFnDependencyNode(destPlug.node()).name()
		srcType = OpenMaya.MFnDependencyNode(srcPlug.node()).typeName()
		destType = OpenMaya.MFnDependencyNode(destPlug.node()).typeName()
		dpName = destPlug.name()
		spName = srcPlug.name()
		listModel = self.listModel
		chk = False
		components = False
		
		if self.objRadio.isChecked() and destType == "objectSet" and dpName.split(".")[1].startswith("dagSetMembers"):
			textPlug = OpenMaya.MFnDependencyNode(destPlug.node()).findPlug("annotation",False).asString()
			if textPlug == "manuListViewSet":
				chk = True
		elif self.shdRadio.isChecked() and destType == "shadingEngine" and dpName.startswith("dagSetMembers"):
			chk = True
		
		if srcType == "mesh" and len(spName.split(".")) > 2:
			chk = False
			
		if srcType == "objectSet" and destType == "mesh":
			textPlug = OpenMaya.MFnDependencyNode(srcPlug.node()).findPlug("annotation",False).asString()
			if textPlug == "manuListViewSet":
				chk = made
				components = True
		
		if chk and not made:
			for dock in self.dockUI:
				if destName == dock.listView.accessibleName():
					break
			listView = dock.listView
			row = listView.findRows([srcName])
			if row:
				listView.setRowHidden(row[0],True)
		elif chk and made:
			if components:
				cmpName = setsListWidget.getComponents(dpName)
				self.connectionItem(srcName,cmpName)
				self.callbackIDs["_%s.%s"%(destName,srcName)] = self.setAttributeCallback(destName,srcName)
				
			else:
				self.connectionItem(destName,[srcName])
	
	def setAttributeCallback(self,name,setName):
		for idName in self.callbackIDs.items():
			if idName[0] == "_%s.%s"%(name,setName):
				try:
					OpenMaya.MMessage.removeCallback(idName[1])
				except:
					pass
		selectionlist = OpenMaya.MSelectionList()
		mobject = OpenMaya.MObject()
		selectionlist.add(setName)
		selectionlist.getDependNode(0, mobject)
		id = OpenMaya.MObjectSetMessage.addSetMembersModifiedCallback(mobject,self.checkChangedAttribute,name)
		return id
	
	def checkChangedAttribute(self ,node, mesh = None):
		setName = OpenMaya.MFnDependencyNode(node).name()
		dockNames = {}
		for dock in self.dockUI:
			if setName == dock.listView.accessibleName():
				listView = dock.listView
		
		listModel = self.listModel
		matchedList = {}
		addObjs = []
		delObjs = []
		
		setA = []
		setB = []
		
		row = listModel.rowCount()
		for i in range(row):
			if not listView.isRowHidden(i):
				setA.append(listModel.item(i).text())
			
		setB = setsListWidget.objExtract(setName)
			
		addObjs = list(filter(lambda x: x not in setA,setB))
		delObjs = list(filter(lambda x: x not in setB,setA))
		
		if addObjs:
			self.connectionItem(setName,addObjs)
		
		if delObjs:
			rows = listView.findRows(delObjs)
			for row in rows:
				listView.setRowHidden(row,True)
	
	def connectionItem(self,setName,data):
		if setName == None:
			listView = self.tabMain.focusWidget()
			setName = listView.accessibleName()
		else:
			for dock in self.dockUI:
				if setName == dock.listView.accessibleName():
					break
			listView = dock.listView
		
		curNo = listView.parentWidget().myNo
		chks = self.appendItemModel(data,curNo)
		rows = listView.findRows(data)
		for chk,row in zip(chks,rows):
			if not chk:
				continue
			listView.setRowHidden(row,False)
			
	def hiliteList(self,chk):
		if chk:
			self.jobNo[0] = setsListWidget.addScriptJobs(self.selectionLists,"selection")
		else:
			setsListWidget.delScriptJobs(self.jobNo[0])
			
	def reloadAllList(self):
		for id in self.callbackIDs.items():
			try:
				OpenMaya.MMessage.removeCallback(id[1])
			except:
				pass
	
		for dock in self.dockUI:
			dock.close()
		self.cnt = 0
		self.dockUI = []
		
		self.buildTabs()
	
	def listViewAndSetName(self):
		listView = self.tabMain.focusWidget()
		setName = listView.accessibleName()
		return listView,setName
	
	def renameSetWindow(self):
		listView,setName = self.listViewAndSetName()
		editWindow = editSetName(setName,self)
		editWindow.show()
	
	def editWindowTitle(self,name):
		listView,setName = self.listViewAndSetName()
		newName = setsListWidget.renameItem(setName,name)
		listView.setAccessibleName(newName)
		listView.parentWidget().setWindowTitle(newName)
		
	
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
			if tabName in setNames:
				continue
			list = setsListWidget.objExtract(tabName)
			self.addTab(tabName,list)
			for item in list:
				meshName = item.split(".")
				if len(meshName)<=1:
					continue
				meshName = meshName[0]
				self.callbackIDs["_%s.%s"%(meshName,tabName)] = self.setAttributeCallback(meshName,tabName)
				
	def delSet(self):
		listView,setName = self.listViewAndSetName()
		setsListWidget.deleteSet(setName)
		dock = listView.parentWidget()
		dock.close()
		self.dockUI.remove(dock)
	
	def remSet(self):
		listView,setName = self.listViewAndSetName()
		setsListWidget.removeSet(setName)
		dock = listView.parentWidget()
		dock.close()
		self.dockUI.remove(dock)
		
	
	def addItem(self):
		_,setName = self.listViewAndSetName()
		data = setsListWidget.addObj(setName)
	
	def removeItem(self):
		listView,setName = self.listViewAndSetName()
		model = listView.model()
		selModel = listView.selectionModel()
		items = []
		
		indexes = selModel.selectedIndexes()
		for index in indexes:
			items.append(model.data(index))
			listView.setRowHidden(index.row(),True)
		setsListWidget.removeObj(setName,items)
		
	def selectAllItem(self):
		setsListWidget.delScriptJobs(self.jobNo[0])
		listView = self.tabMain.focusWidget()
		curNo = listView.parentWidget().myNo
		setName = listView.accessibleName()
		objs = setsListWidget.selectAll(setName)
		listView.selectAll()
		self.jobNo[0] = setsListWidget.addScriptJobs(self.selectionLists,"selection")
				
	def clearItem(self):
		listView,setName = self.listViewAndSetName()
		setsListWidget.clearSet(setName)
		listModel = self.listModel
		row = listModel.rowCount()
		for i in range(row):
			listView.setRowHidden(i,True)
	
	def appendItemModel(self,data,curID = None):
		listModel = self.listModel
		instID = ListField.instID
		chks = []
		if not data:
			return chks
		for node in data:
			item = listModel.findItems(node)
			if item:
				chks.append(True)
			else:
				listModel.appendRow(QStandardItem(node))
				for id in instID:
					if id == curID:
						continue
					row = listModel.rowCount()
					self.dockUI[id].listView.setRowHidden((row-1),True)
				chks.append(False)
		return chks
		
def main():
	app = QApplication.instance()
	ui = SetsListUI()
	sys.exit()
	app.exec_()

if __name__ == "__main__":
	main()