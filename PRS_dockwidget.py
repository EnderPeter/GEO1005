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
#from Qt import QtCore
from qgis._core import QgsRectangle, QgsProject
from qgis._networkanalysis import QgsLineVectorLayerDirector, QgsDistanceArcProperter, QgsGraphBuilder, QgsGraphAnalyzer
from qgis.utils import iface
from qgis._core import QgsMapLayerRegistry, QgsDataSourceURI, QgsRectangle, QgsVectorLayer
from qgis.networkanalysis import *
import processing
from . import utility_functions as uf
import resources


import random

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'PRS_dockwidget_base.ui'))

class PRS_PoliceResponseSystemDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    layer_dic=dict()
    police_station_id = dict()
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
        self.loadSituation.clicked.connect(self.load_situation)
        self.comboIncident.activated.connect(self.setIncident)
        self.fixPosition.clicked.connect(self.fix)
        self.fixPosition2.clicked.connect(self.fix)

        #analysis
        #self.setNetworkButton.clicked.connect(self.buildNetwork)
        self.buffer_zone.clicked.connect(self.calculateBuffer)
        self.shortestPath.clicked.connect(self.run_shortest_path)
        self.intersection_button.clicked.connect(self.intersection_block)

        #Shortest path table signals
        self.shortestPathTable.itemClicked.connect(self.selection_shortest_path_table)

        # roadblock_table signal
        self.roadblock_table.itemClicked.connect(self.select_roadblock_table)

        #Decision Tab
        self.PoliceStationButton.clicked.connect(self.SelectPoliceStation)
        self.ShowInformationButton.clicked.connect(self.ShowInformation)
        self.deployTeam.clicked.connect(self.DeployTeam)
        self.GenerateReportButton.clicked.connect(self.generatereport)

        #remove layers
        self.clear_points.clicked.connect(self.clean)

        self.graph = QgsGraph()
        self.tied_points = []
        self.shortestPathTable.clear()

    def closeEvent(self, event):

        self.closingPlugin.emit()
        self.shortestPathTable.clear()
        self.shortestPathTable.clear()
        self.PoliceTable.clear()
        self.ReportInformation.clear()
        event.accept()

    def load_situation(self):

        self.comboIncident.setEnabled(True)
        osm = uf.getLegendLayerByName(self.iface, "OSM")
        self.iface.legendInterface().setLayerVisible(osm, True)

        #zoon to Layer
        self.iface.mapCanvas().setExtent(QgsRectangle(491948.924266, 6779060, 504837, 6787990))
        self.iface.mapCanvas().refresh()

        #loading layers from spatialite database
        self.load_layer_from_db("Study_area", "study_area.qml")
        self.load_layer_from_db("RoadNetwork", "road_network.qml")
        self.load_layer_from_db("Police_stations_area", "police_station.qml")
        self.load_layer_from_db("Buffer_A", "buffer_a.qml")
        self.load_layer_from_db("Buffer_B", "buffer_b.qml")
        self.load_layer_from_db("info_A", "info_A.qml")
        self.load_layer_from_db("info_B", "info_B.qml")
        self.load_layer_from_db("Incident_A", "incident_a.qml")
        self.load_layer_from_db("Incident_B", "incident_b.qml")

        #Add Items to ComboboxIncident
        self.comboIncident.clear()
        self.comboIncident.addItem("-")
        self.comboIncident.addItem("Incident_A")
        self.comboIncident.addItem("Incident_B")

        #Add SVG Markers
        infoA = uf.getLegendLayerByName(self.iface,"info_A")
        infoB= uf.getLegendLayerByName(self.iface,"info_B")
        layer_svg = [infoA,infoB]

        for item in  layer_svg:
            cur_dir = os.path.dirname(os.path.realpath(__file__))
            terrorist_marker = os.path.join(cur_dir, "data", "markers", "thief.svg")
            svg_style_terrorist = dict()
            svg_style_terrorist['name']=terrorist_marker
            svg_style_terrorist['size']='5'

            guns_marker = os.path.join(cur_dir, "data", "markers", "guns.svg")
            svg_style_guns = dict()
            svg_style_guns['name'] = guns_marker
            svg_style_guns['size'] = '16'

            hostage_marker = os.path.join(cur_dir, "data", "markers", "hostage.svg")
            svg_style_hostage = dict()
            svg_style_hostage['name'] = hostage_marker
            svg_style_hostage['size'] = '7.5'

            symLyr1 = QgsMarkerSymbolV2.createSimple({"color" : "255,255,255","color_border": "0,0,0",'outline_width': '0.0','size': '0.3'})
            symLyr1.appendSymbolLayer(QgsSvgMarkerSymbolLayerV2.create(svg_style_terrorist))
            symLyr2 = QgsMarkerSymbolV2.createSimple({"color": "255,255,255", "outline": "255,255,255", 'outline_width': '0.0', 'size': '0.3'})
            symLyr2.appendSymbolLayer(QgsSvgMarkerSymbolLayerV2.create(svg_style_guns))
            symLyr3 = QgsMarkerSymbolV2.createSimple({"color" : "255,255,255","outline" :"255,255,255",'outline_width': '0.0','size': '0.3'})
            symLyr3.appendSymbolLayer(QgsSvgMarkerSymbolLayerV2.create(svg_style_hostage))

            # create renderer object
            fni = item.fieldNameIndex('PK_UID')
            unique_values = item.dataProvider().uniqueValues(fni)

           # print unique_values
            category1 = QgsRendererCategoryV2(str(unique_values[0]), symLyr1, str(unique_values[0]))
            category2 = QgsRendererCategoryV2(str(unique_values[1]), symLyr2, str(unique_values[1]))
            category3 = QgsRendererCategoryV2(str(unique_values[2]), symLyr3, str(unique_values[2]))

            # entry for the list of category items
            categories=[]
            categories.append(category1)
            categories.append(category2)
            categories.append(category3)
            renderer = QgsCategorizedSymbolRendererV2('PK_UID', categories)
            item.setRendererV2(renderer)

    def fix(self):
        self.iface.mapCanvas().setExtent(QgsRectangle(491948.924266, 6779060, 504837, 6787990))
        self.iface.mapCanvas().refresh()


    def load_layer_from_db(self, layer_name,style_name):
        #load layers from spatialite database
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
        self.bufferCutoffEdit.setEnabled(True)
        self.buffer_zone.setEnabled(True)
        self.shortestPath.setEnabled(True)
        self.ReportInformation.setEnabled(True)
        layer_name = self.comboIncident.currentText()
        self.selected_layer = layer_name
        print layer_name
        if layer_name == "Incident_A":

            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), False)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_A"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_B"), False)

            global report
            report = []
            feature = self.layer_dic.get("Incident_A").getFeatures().next()
            report.append("\nLevel of Threat (LOT) : {0}".format(feature.attribute("LOT")))
            report.append("Location : {0}".format(feature.attribute("Location")))
            report.append("Address : {0}".format(feature.attribute("Address")))
            report.append("Timestamp : {0}".format(feature.attribute("Timestamp")))
            report.append("Attackers : {0}".format(feature.attribute("Attackers")))
            report.append("Weapons : {0}".format(feature.attribute("Weapons")))
            report.append("Casualties : {0}".format(feature.attribute("Casualties")))
            report.append("Radius : {0}".format(feature.attribute("Radius")))
            report.append("Link : {0}".format(feature.attribute("Link")))
            self.ReportInformation.clear()
            self.ReportInformation.addItems(report)


        elif layer_name == "Incident_B":
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), False)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_A"), False)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_B"), True)

            global report
            report = []
            feature = self.layer_dic.get("Incident_B").getFeatures().next()
            report.append("\nLevel of Threat (LOT) : {0}".format(feature.attribute("LOT")))
            report.append("Location : {0}".format(feature.attribute("Location")))
            report.append("Address : {0}".format(feature.attribute("Adress")))
            report.append("Timestamp : {0}".format(feature.attribute("Timestamp")))
            report.append("Attackers : {0}".format(feature.attribute("Attackers")))
            report.append("Weapons : {0}".format(feature.attribute("Weapons")))
            report.append("Casualties : {0}".format(feature.attribute("Casualties")))
            report.append("Radius : {0}".format(feature.attribute("Radius")))
            report.append("Link : {0}".format(feature.attribute("Link")))
            self.ReportInformation.clear()
            self.ReportInformation.addItems(report)

        elif layer_name == "-":
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"),True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_A"), True)
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("info_B"), True)


    # buffer functions
    def getBufferCutoff(self):
        cutoff = self.bufferCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateBuffer(self):

        self.intersection_button.setEnabled(True)

        #clean Buffer
        if len(self.danger_zones)>0:
            for buffer in self.danger_zones:
                QgsMapLayerRegistry.instance().removeMapLayer(buffer.id())
            self.danger_zones = []

        #layer = uf.getLegendLayerByName(self.iface, "Incident_A")
        layer = uf.getLegendLayerByName(self.iface, self.selected_layer)
        origins = layer.getFeatures()

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
                buffer_layer.setLayerTransparency(55)

                ###Colorif layer_name ==incident use color xx xx
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

    def setZone(self):
        for buffer in self.danger_zones:
            layer_name = self.danger_zones
            self.textDanger = layer_name


    ###### Roads Block Points
    def intersection_block(self):
        self.clear_points.setEnabled(True)
        processing.runandload('qgis:polygonstolines', 'Danger_Zone', 'memory:Lines from polygons')
        processing.runandload('qgis:lineintersections', 'Lines from polygons', 'RoadNetwork', None, None, 'memory:Intersections')


    def clean (self):
        lines_polygons_layer = uf.getLegendLayerByName(self.iface, "Lines from polygons")
        intersection_layer = uf.getLegendLayerByName(self.iface, "Intersections")
        QgsMapLayerRegistry.instance().removeMapLayer(intersection_layer.id())
        QgsMapLayerRegistry.instance().removeMapLayer(lines_polygons_layer.id())
        self.roadblock_table.clear()

    '''Line 340'''

    ###### Roads Block Points
    def intersection_block(self):
        self.clear_points.setEnabled(True)
        processing.runandload('qgis:polygonstolines', 'Danger_Zone', 'memory:Lines from polygons')
        processing.runandload('qgis:lineintersections', 'Lines from polygons', 'RoadNetwork', None, None,
                              'memory:Intersections')
        self.addfield_xy()
        self.calculate_coordinate()
        roadblocks = self.save_coordinates()
        count_roadblocks = len(roadblocks)
        # initiate roadblocks table
        self.roadblock_table.clear()
        self.roadblock_table.setColumnCount(3)
        self.roadblock_table.setHorizontalHeaderLabels(["id", "X", "Y"])
        self.roadblock_table.setRowCount(count_roadblocks)
        # populate roadblock table
        for roadblock in roadblocks:
            self.populate_roadblocktable(roadblock[0] - 1, roadblock[0], roadblock[1],
                                         roadblock[2])  # -1, otherwise will start from second row

    def populate_roadblocktable(self, item_number, id, X, Y):
        self.roadblock_table.setItem(item_number, 0, QtGui.QTableWidgetItem(unicode(id)))
        self.roadblock_table.setItem(item_number, 1, QtGui.QTableWidgetItem(unicode(X)))
        self.roadblock_table.setItem(item_number, 2, QtGui.QTableWidgetItem(unicode(Y)))

    ''' Xin's part. Function used to add field to a table'''

    def addfield_xy(self):
        layer = uf.getLegendLayerByName(self.iface, "Intersections")
        names = ['id', 'X', 'Y']
        types = [QVariant.Int, QVariant.String, QVariant.String]
        uf.addFields(layer, names, types)

    '''Function used to calculate coordinate of each road block'''

    def calculate_coordinate(self):
        layer = uf.getLegendLayerByName(self.iface, "Intersections")
        name_id = 'id'
        name_x = 'X'
        name_y = 'Y'
        expression_id = '$rownum'  # expression to get unique incremental id for each row (feature)
        expression_x = '$x'
        expression_y = '$y'
        uf.updateField(layer, name_id, expression_id)
        uf.updateField(layer, name_x, expression_x)
        uf.updateField(layer, name_y, expression_y)

    '''Function to save roadblocks' id and coordinates in variable'''

    def save_coordinates(self):
        layer = uf.getLegendLayerByName(self.iface, "Intersections")
        field_x = 'X'
        field_y = 'Y'
        X_and_id = uf.getFieldValues(layer, field_x, null=True, selection=False)
        Y_and_id = uf.getFieldValues(layer, field_y, null=True, selection=False)
        id_and_coordinate = list(zip(X_and_id[1], X_and_id[0], Y_and_id[0]))
        return id_and_coordinate

    ''' Function used to select roadblocks in roadblock_table'''  # something wrong here, still working on that.

    def select_roadblock_table(self):
        if len(self.roadblock_table.selectedItems()) == 1:
            id_qtable = self.roadblock_table.selectedItems()[0]
            layer = uf.getLegendLayerByName(self.iface, "Intersections")
            selection = []
            for feature in layer.getFeatures():
                if feature.attribute("id") == id_qtable:
                    selection.append(feature.id())
            layer.setSelectedFeatures(selection)


    ###### Shortest Path
    def select_origins_and_dest(self,orig,dest):
        ps1_road_id = QgsExpression(orig)
        incident_road_id = QgsExpression(dest)
        it = self.layer_dic.get("RoadNetwork").getFeatures(QgsFeatureRequest(ps1_road_id))
        it2 = self.layer_dic.get("RoadNetwork").getFeatures(QgsFeatureRequest(incident_road_id))
        ids1 = [i.id() for i in it]
        ids2 = [i.id() for i in it2]
        self.layer_dic.get("RoadNetwork").setSelectedFeatures(ids1+ids2)

    def run_shortest_path(self,dest):
        # load information from police stations
        layer_shortest = uf.getLegendLayerByName(self.iface, "Police_stations_info")

        if not layer_shortest:
            self.load_layer_from_db("Police_stations_info", "police_station_info.qml")

        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        layer_name = self.comboIncident.currentText()
        if layer_name == "Incident_A":
            if routes_layer:
                QgsMapLayerRegistry.instance().removeMapLayer(routes_layer.id())
            dest = "\"PK_UID\"=6520"

        else:
            if routes_layer:
                QgsMapLayerRegistry.instance().removeMapLayer(routes_layer.id())
            dest=  "\"PK_UID\"=2782"

             #origin and destinations
        orig = ["\"PK_UID\"=6482","\"PK_UID\"=7505","\"PK_UID\"=6661", "\"PK_UID\"=6618","\"PK_UID\"=5368","\"PK_UID\"=1112"]
        lengths = []
        for i in range(len(orig)):
            self.select_origins_and_dest(orig[i],dest); #Origins and Dest
            self.buildNetwork();
            self.calculateRoute(i);
            lengths.append(self.calculate_length(i+1))
        #lenghts by tab
        textBox = dict()
        textBox["Zeehaven (ZH)        "] =  lengths[0]
        textBox["Zuidplein (ZP)           "] = lengths[1]
        textBox["Boezemsingel (BZ)    "] = lengths[2]
        textBox["Marconiplein (MP)    "] = lengths[3]
        textBox["Targer Water (TW)    "] = lengths[4]
        textBox["Tabor Street (TS)    "] = lengths[5]

        #police station attrib ids
        self.police_station_id["Zeehaven (ZH)"] = 0
        self.police_station_id["Zuidplein (ZP)"] = 1
        self.police_station_id["Boezemsingel (BZ)"] = 2
        self.police_station_id["Marconiplein (MP)"] = 3
        self.police_station_id["Targer Water (TW)"] = 4
        self.police_station_id["Tabor Street (TS)"] = 5

        #sort by near police station
        format_results = ""
        self.init_shortestPathTable()
        count = 0
        for key, value in sorted(textBox.iteritems(), key=lambda (k,v): (v,k)):
            self.populate_shortestPathTable(count,key, str(round(textBox[key]/1000.0, 2))+" km")
            count = count + 1
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

                symbols = routes_layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setWidth(0.8)
                symbol.setColor(QColor.fromRgb(15, 152, 9))
                uf.loadTempLayer(routes_layer)
            uf.insertTempFeatures(routes_layer, [path], [[name_feature, 100.00]])
            #buffer = processing.runandload('qgis:fixeddistancebuffer', routes_layer, 10.0, 5, False, None)
            self.refreshCanvas(routes_layer)

    #create routes legths table
    def init_shortestPathTable(self):
        self.shortestPathTable.clear()
        self.shortestPathTable.setColumnCount(2)
        self.shortestPathTable.setHorizontalHeaderLabels(["Police Station", "Distance"])
        self.shortestPathTable.setRowCount(6)

    #populate routes legths table
    def populate_shortestPathTable(self,item_number,station,distance):
        self.shortestPathTable.setItem(item_number, 0, QtGui.QTableWidgetItem(unicode(station)))
        self.shortestPathTable.setItem(item_number, 1, QtGui.QTableWidgetItem(unicode(distance)))

    def selection_shortest_path_table(self):

        if len(self.shortestPathTable.selectedItems()) == 1 :
            key = self.shortestPathTable.selectedItems()[0].text().encode('ascii', 'ignore').strip()
            if self.police_station_id.has_key(key):
                id = self.police_station_id[key]
                layer = uf.getLegendLayerByName(self.iface,"Routes")
                selection = layer.getFeatures(QgsFeatureRequest().setFilterExpression( unicode("id="+str(id))))
                for k in selection:
                    print k
                    layer.setSelectedFeatures([k.id()])

    def SelectPoliceStation(self):
        self.ShowInformationButton.setEnabled(True)
        layer=uf.getLegendLayerByName(self.iface, "Police_stations_area")
        self.iface.setActiveLayer(layer)
        self.iface.actionSelect().trigger()

        #set police layer as working layer

    def getvehicles(self):
        cutoff_vehicles = self.vehicles.text()
        if uf.isNumeric(cutoff_vehicles):
            return uf.convertNumeric(cutoff_vehicles)
        else:
            return 0

    def getofficers(self):
        cutoff_officers = self.officers.text()
        if uf.isNumeric(cutoff_officers):
            return uf.convertNumeric(cutoff_officers)
        else:
            return 0
    global ListDeploy
    ListDeploy=[]


    def DeployTeam(self):

        vehicles = self.getvehicles()
        officers = self.getofficers()
        featurePol = self.getFeature()

        namePol = featurePol.attribute("name")
        text="PT {0}  Vehicles: {1} Officers: {2}\n".format(namePol,vehicles,officers)
        ListDeploy.append(text)
    def generatereport(self):
        final=""
        for i in range(len(ListDeploy)):
            final=final+ListDeploy[i]
        print final

        print report

        ReportText="Incident Report\n {0}\n {1}\n {2}\n {3}\n" \
                   "{4}\n {5}\n {6}\n {7}\n {8} \n" \
                   "Police Officers Involved\n\n\n\n" \
                   "{9}".format(report[0],report[1],report[2],report[3],report[4],report[5],report[6],report[7],report[8],final)
        print ReportText
        self.ReportText.insertPlainText(ReportText)
    def getFeature(self):
        layer=self.iface.activeLayer()
        features =layer.selectedFeatures()
        feature = features[0]
        return feature

    def ShowInformation(self):

        feature = self.getFeature()

        PoliceData = (feature.attribute("name"), feature.attribute("n_vehicle"), feature.attribute("n_officer"),
                      feature.attribute("equipment"))
        self.clearTable()
        self.updateTable(PoliceData)

    def updateTable(self,values):
        #take a tuple with the values of one feature
        self.PoliceTable.setColumnCount(4)
        self.PoliceTable.setHorizontalHeaderLabels(["name","vehicles","officers","equipments"])
        self.PoliceTable.setRowCount(1)

            #item must be added as QTableWidgetItems
        self.PoliceTable.setItem(0,0,QtGui.QTableWidgetItem(unicode(values[0])))
        self.PoliceTable.setItem(0,1,QtGui.QTableWidgetItem(unicode(values[1])))
        self.PoliceTable.setItem(0,2,QtGui.QTableWidgetItem(unicode(values[2])))
        self.PoliceTable.setItem(0,3,QtGui.QTableWidgetItem(unicode(values[3])))

        '''self.PoliceTable.horizontalHeader().setResizeMode(0,QtQui.QHeaderView.Strech)
        self.PoliceTable.horizontalHeader().setResizeMode(1,QtQui.QHeaderView.Strech)
        self.PoliceTable.horizontalHeader().setResizeMode(2,QtQui.QHeaderView.Strech)
        self.PoliceTable.horizontalHeader().setResizeMode(3,QtQui.QHeaderView.Strech)'''

    def clearTable(self):
        self.PoliceTable.clear()

