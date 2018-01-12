# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PRS_PoliceResponseSystemDockWidget
                                 A QGIS plugin
 Support decisions of police officers in catching terrorist attackers at the least possible cost.
                             -------------------
        begin                : 2018-01-04
        git sha              : $Format:%H$
        copyright            : (C) 2018 by TUDelft
        email                : meylinh52@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from numpy import random
from qgis.core import *
from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal, Qt, QVariant
from PyQt4.QtGui import QColor
from Qt import QtCore
from qgis._core import QgsRectangle, QgsProject
from qgis._networkanalysis import QgsLineVectorLayerDirector, QgsDistanceArcProperter, QgsGraphBuilder, QgsGraphAnalyzer
from qgis.utils import iface
from qgis._core import QgsMapLayerRegistry, QgsDataSourceURI, QgsRectangle, QgsVectorLayer
from qgis.networkanalysis import *
import processing
from . import utility_functions as uf

import random

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'PRS_dockwidget_base.ui'))


class PRS_PoliceResponseSystemDockWidget(QtGui.QDockWidget, FORM_CLASS):


    closingPlugin = pyqtSignal()
    layer_dic=dict()
    danger_zones=[]
    selected_Incident = "-"
    #selected_layer="Incident_A"
    textDanger= "-"


    def __init__(self, parent=None):
        """Constructor."""
        super(PRS_PoliceResponseSystemDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # Init OpenStreet Map Layer
        self.canvas.useImageToRender(False)
        self.canvas.setCanvasColor(Qt.white)
        self.canvas.show()

        # data
        self.openScenario.clicked.connect(self.zoom)
        #self.incident_a.clicked.connect(self.removeMapLayersB)
        #self.incident_b.clicked.connect(self.removeMapLayersA)
        #self.selectLayerCombo.activated.connect(self.setSelectedLayer)
        self.comboIncident.activated.connect(self.setIncident)
        #self.comboIncident.activated.connect(self.removeMapLayersB)
        #self.comboIncident.activated.connect(self.removeMapLayersA)
        #analysis
        #self.setNetworkButton.clicked.connect(self.buildNetwork)
        self.buffer_zone.clicked.connect(self.calculateBuffer)
        self.shortestPath.clicked.connect(self.run_shortest_path)
        #self.selectZone.activated.connect(self.setZone)
        self.intersection_button.clicked.connect(self.intersection_block)
        self.show_path_length.clicked.connect(self.calculate_length)

        # # #remove layers
        self.clean_buffer.clicked.connect(self.cleanBuffer)

        self.graph = QgsGraph()
        self.tied_points = []
        self.resultTextEdit.clear()


    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.resultTextEdit.clear()
        event.accept()

    def zoom(self):
        self.iface.mapCanvas().setExtent(QgsRectangle(491948.924266, 6779060, 504837, 6787990))
        self.iface.mapCanvas().refresh()

        self.load_layer_from_db("Study_area", "study_area.qml")
        self.load_layer_from_db("RoadNetwork", "road_network.qml")
        self.load_layer_from_db("Police_stations_area", "police_station.qml")
        self.load_layer_from_db("Buffer_A", "buffer_a.qml")
        self.load_layer_from_db("Buffer_B", "buffer_b.qml")
        self.load_layer_from_db("info_A", "info_A.qml")
        self.load_layer_from_db("Incident_A", "incident_a.qml")
        self.load_layer_from_db("Incident_B", "incident_b.qml")

        #Add Items to ComboboxIncident
        self.comboIncident.clear()
        self.comboIncident.addItem("-")
        self.comboIncident.addItem("Incident_A")
        self.comboIncident.addItem("Incident_B")


    def load_layer_from_db(self, layer_name,style_name):
        uri = QgsDataSourceURI()
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(cur_dir, "data", "db.sqlite")
        filename_styles = os.path.join(cur_dir, "data", "styles",style_name)
        uri.setDatabase(filename)
        uri.setDataSource('', layer_name, 'GEOMETRY', )
        sta = QgsVectorLayer(uri.uri(), layer_name, "spatialite")
        sta.loadNamedStyle(filename_styles)
        # set the transparency of a layer
        # sta.setLayerTransparency(89)
        self.layer_dic[layer_name]=sta
        QgsMapLayerRegistry.instance().addMapLayers([sta])


    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    def setIncident(self):
        layer_name = self.comboIncident.currentText()
        self.selected_layer = layer_name
        if layer_name == "Incident_A":
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), False)
        elif layer_name == "Incident_B":
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), False)

    # buffer functions
    def getBufferCutoff(self):
        cutoff = self.bufferCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateBuffer(self):
        #layer = uf.getLegendLayerByName(self.iface, "Incident_A")
        layer = uf.getLegendLayerByName(self.iface, self.selected_layer)
        origins = layer.getFeatures()
        #origins = self.getSelectedLayer().selectedFeatures()
        #layer = self.getSelectedLayer()
        if origins > 0:
            cutoff_distance = self.getBufferCutoff()
            buffers = {}
            #print "cutt_off ",cutoff_distance
            print "origins ", origins
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()

            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QVariant.String, QVariant.Double]
                buffer_layer = uf.createTempLayer('Buffers','POLYGON',layer.crs().postgisSrid(), attribs, types)
                buffer_layer.setLayerTransparency(20)

                ###Colorif layer_name ==incien_a use color xx xx
                symbols = buffer_layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(QColor.fromRgb(255, 255, 50))
                ###

                #uf.loadTempLayer(buffer_layer)
                QgsMapLayerRegistry.instance().addMapLayer(buffer_layer, False)
                root = QgsProject.instance().layerTreeRoot()
                root.insertLayer(6, buffer_layer)
                buffer_layer.setLayerName('Danger_Zone')
                self.danger_zones.append(buffer_layer)
            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0],cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.refreshCanvas(buffer_layer)

    def cleanBuffer(self):
        for buffer in self.danger_zones:
             QgsMapLayerRegistry.instance().removeMapLayer(buffer.id())
        self.danger_zones=[]


    def setZone(self):
        for buffer in self.danger_zones:
            layer_name = self.danger_zones
            self.textDanger = layer_name


    ###### Block Points

    def intersection_block(self):
        processing.runandload('qgis:polygonstolines', 'Danger_Zone', 'memory:Lines from polygons')
        processing.runandload('qgis:lineintersections', 'Lines from polygons', 'RoadNetwork', None, None, 'memory:Intersections')



    ###### Shortest Path

    def select_origins_and_dest(self,orig,dest):
        ps1_road_id = QgsExpression(orig)
        incident_a_road_id = QgsExpression(dest)
        it = self.layer_dic.get("RoadNetwork").getFeatures(QgsFeatureRequest(ps1_road_id))
        it2 = self.layer_dic.get("RoadNetwork").getFeatures(QgsFeatureRequest(incident_a_road_id))
        ids1 = [i.id() for i in it]
        ids2 = [i.id() for i in it2]
        self.layer_dic.get("RoadNetwork").setSelectedFeatures(ids1+ids2)

    def run_shortest_path(self):
        orig = ["\"PK_UID\"=6482","\"PK_UID\"=7505","\"PK_UID\"=6661", "\"PK_UID\"=6618","\"PK_UID\"=5368","\"PK_UID\"=1112"]
        dest = "\"PK_UID\"=6520"
        lengths = []
        for i in range(len(orig)):
            self.select_origins_and_dest(orig[i],dest); #Origins and Dest
            self.buildNetwork();
            self.calculateRoute(i);
            lengths.append(self.calculate_length(i+1))
        self.resultTextEdit.clear()
        #lenghts by tab
        textBox = dict()
        textBox["PS1"]=lengths[0]
        textBox["PS2"] = lengths[1]
        textBox["PS3"] = lengths[2]
        textBox["PS4"] = lengths[3]
        textBox["PS5"] = lengths[4]
        textBox["PS6"] = lengths[5]

        #sort by near police station
        format_results = ""
        for key, value in sorted(textBox.iteritems(), key=lambda (k,v): (v,k)):
            self.resultTextEdit.insertPlainText(key)
            self.resultTextEdit.insertPlainText("\t")
            self.resultTextEdit.insertPlainText(str(round(textBox[key]/1000.0, 2))+" km")
            self.resultTextEdit.insertPlainText("\n")
            self.resultTextEdit.insertPlainText("\n")
        #print format_results
        #self.resultTextEdit.insertPlainText(format_results)


        # Function to calculate length of all shortest path, one thing to notice: If there're more than one path to calculate length, length should be a list, not a variable.
    def calculate_length(self,id):
        layer = uf.getLegendLayerByName(self.iface, "Routes")
        for path in layer.getFeatures(QgsFeatureRequest(id)):
            return  path.geometry().length()

    def getNetwork(self):

        # layer = uf.getLegendLayerByName(self.iface, "Incident_A")
        roads_layer = uf.getLegendLayerByName(self.iface,"RoadNetwork" )
        #roads_layer = layer.getFeatures()
        # roads_layer = self.getSelectedLayer()
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network', 'LINESTRING', roads_layer.crs().postgisSrid(), [], [])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network
        else:
            return

    def buildNetwork(self):

        self.network_layer = self.getNetwork()
        if self.network_layer:
            # get the points to be used as origin and destination
            # in this case gets the centroid of the selected features
            layer = uf.getLegendLayerByName(self.iface, "RoadNetwork")
            selected_sources = self.layer_dic.get("RoadNetwork").selectedFeatures()
            # selected#_sources = self.getSelectedLayer().selectedFeatures()
            source_points = [feature.geometry().centroid().asPoint() for feature in selected_sources]
            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
                # the tied points are the new source_points on the graph
                #if self.graph and self.tied_points:
                    #text = "network is built for %s points" % len(self.tied_points)
                    #self.insertReport(text)
        return

    def calculateRoute(self, name_feature):

        # origin and destination must be in the set of tied_points
        options = len(self.tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0
            destination = random.randint(1, options - 1)
            # calculate the shortest path for the given origin and destination
            path = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
            # store the route results in temporary layer called "Routes"
            routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
#            print routes_layer
            # create one if it doesn't exist
            if not routes_layer:
                attribs = ['id']
                types = [QtCore.QVariant.String]
                routes_layer = uf.createTempLayer('Routes', 'LINESTRING', self.network_layer.crs().postgisSrid(),
                                                  attribs, types)
                uf.loadTempLayer(routes_layer)
            # insert route line
 #           for route in routes_layer.getFeatures():
 #               print route.id()
            uf.insertTempFeatures(routes_layer, [path], [[name_feature, 100.00]])

            buffer = processing.runandload('qgis:fixeddistancebuffer', routes_layer, 10.0, 5, False, None)
            self.refreshCanvas(routes_layer)

