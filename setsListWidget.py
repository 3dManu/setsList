#!/usr/bin/env python
# -*- coding: utf-8 -*-

import maya.cmds as cmds

def setsExtract(type):
	stop_undo()
	getSets = cmds.ls(set = True)
	remSets = ["defaultLightSet","defaultObjectSet","defaultCreaseDataSet","swatchShadingGroup","TurtleDefaultBakeLayer"]
	sgSets = cmds.ls(type = "shadingEngine")
	filterSG = list(filter(lambda x: x not in sgSets,getSets))
	for sg in filterSG:
		deformChk = cmds.connectionInfo(sg+".usedBy[0]",id = True)
		if deformChk:
			remSets.append(sg)
			
		txtChk = cmds.sets(sg,q=True,t=True)
		if txtChk != "manuListViewSet":
			remSets.append(sg)
	
	objSets = list(filter(lambda x: x not in remSets,filterSG))
	if type:
		sets = objSets
	else:
		sets = sgSets
	start_undo()
	
	return sets
	
def objExtract(set):
	stop_undo()
	nullSet = cmds.sets(em=True,name="nullSet")
	objs = cmds.sets(set,un = nullSet)
	cmds.delete(nullSet)
	start_undo()
	
	return objs
	
def selectAll(set):
	objs = objExtract(set)
	cmds.select(objs,r=True)
	return objs
	

def addObj(set):
	getObj = cmds.ls(sl=True)
	cmds.sets(getObj,e=True,fe=set)
	return getObj

def removeObj(set,objs):
	cmds.sets(objs,e=True,rm=set)
	
def clearSet(set):
	cmds.sets(e=True,cl=set)

def createSet(name):
	cmds.sets(em=True,name=name,text="manuListViewSet")
	
def removeSet(name):
	cmds.sets(name,e=True,text="Unnamed object set")

def selectObjs(objs):
	cmds.select(objs,r=True)

def selectLists():
	names = cmds.ls(sl=True)
	return names

def addSetTab():
	sets = cmds.ls(sl=True,set=True)
	for set in sets:
		cmds.sets(set,e=True,text="manuListViewSet")
	if sets:
		return sets
	else:
		print "plz select sets."

def deleteSet(name):
	cmds.delete(name)
	
def addScriptJobs(cmd,typ):
	if typ == "selection":
		i = cmds.scriptJob(e=["SelectionChanged",cmd])
		return i
	elif typ == "delete":
		i = cmds.scriptJob(ct=["delete",cmd])
		return i
	else:
		i = cmds.scriptJob(e=["renderLayerManagerChange",cmd])
		return i

def delScriptJobs(no):
	if cmds.scriptJob(ex = no):
		cmds.scriptJob(kill=no, force=True)

def renameItem(obj,name):
	adjName = cmds.rename(obj,name)
	return adjName
	
def open_undo(name):
	cmds.undoInfo(openChunk=True,chunkName = name)
def close_undo(name):
	cmds.undoInfo(closeChunk=True,chunkName = name)
	
def start_undo():
	cmds.undoInfo(stateWithoutFlush=True)
def stop_undo():
	cmds.undoInfo(stateWithoutFlush=False)