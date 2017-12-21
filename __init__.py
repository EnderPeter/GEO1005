# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PRS_PoliceResponseSystem
                                 A QGIS plugin
 Support decision of police officicers when catching a terrorist
                             -------------------
        begin                : 2017-12-20
        copyright            : (C) 2017 by TUDelft
        email                : meylinh52@gmail.com
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
    """Load PRS_PoliceResponseSystem class from file PRS_PoliceResponseSystem.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .PRS import PRS_PoliceResponseSystem
    return PRS_PoliceResponseSystem(iface)
