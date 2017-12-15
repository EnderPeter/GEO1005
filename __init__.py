# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SDSS_terrist_catch
                                 A QGIS plugin
 Catching Criminals
                             -------------------
        begin                : 2017-12-13
        copyright            : (C) 2017 by TUDelft
        email                : meylinnh52@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SDSS_terrist_catch class from file SDSS_terrist_catch.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Test import SDSS_terrist_catch
    return SDSS_terrist_catch(iface)
