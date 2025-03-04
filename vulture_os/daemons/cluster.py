#!/home/vlt-os/env/bin/python
"""This file is part of Vulture 3.

Vulture 3 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Vulture 3 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Vulture 3.  If not, see http://www.gnu.org/licenses/.
"""
__author__ = "Jérémie JOURDIN"
__credits__ = ["Kevin GUILLEMOT"]
__license__ = "GPLv3"
__version__ = "4.0.0"
__maintainer__ = "Vulture OS"
__email__ = "contact@vultureproject.org"
__doc__ = 'Cluster daemon'


import os
import sys
import time

# Django setup part
sys.path.append('/home/vlt-os/vulture_os')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'vulture_os.settings')

import django
from django.conf import settings
django.setup()

import logging
logging.config.dictConfig(settings.LOG_SETTINGS)
logger = logging.getLogger('daemon')

from system.cluster.models import Cluster
from services.pf.pf import PFService
from daemons.monitor import MonitorJob
from services.exceptions import ServiceExit
from signal import signal, SIGTERM, SIGINT


def service_shutdown(signum, frame):
    print('Caught signal %d' % signum)
    raise ServiceExit


""" This is for the cluster daemon process """
if __name__ == '__main__':
    """ Launch monitor job """
    monitor_job = MonitorJob(10)
    monitor_job.start()

    signal(SIGTERM, service_shutdown)
    signal(SIGINT, service_shutdown)

    error = False
    this_node = None

    """ Continue as a daemon """
    while True:
        try:
            """ May be False for pending new nodes """
            if this_node:

                # Process messages FIRST
                """ Process inter-cluster messages """
                this_node.process_messages()

                if error:
                    logger.info("Cluster::daemon: Recovered from previous failure")
                    error = False
            else:
                this_node = Cluster.get_current_node()

            time.sleep(5)

        except ServiceExit as e:
            """ Exiting asked """
            logger.info("Cluster::daemon: Exit asked.")
            break
        except Exception as e:
            # Try to log, in case of Mongodb failure
            try:
                logger.error("Cluster::daemon: General failure: {}".format(str(e)))
            except ServiceExit:
                """ Exiting asked """
                print("Cluster::daemon: Exit asked.")
                break
            except Exception as e:
                print("Cluster::daemon: General failure: {}".format(str(e)))

            try:
                pf = PFService()
                stats = pf.get_rules()
                # If PF enabled and 0 rules loaded
                if len(stats) == 0:
                    logger.info("Cluster::daemon: Loading pf rules")
                    # Reload PF with conf file - in case of boot issue (e.g: domain in config file)
                    pf.reload()
            except ServiceExit:
                print("Cluster::daemon: Exit asked.")
                break
            except Exception as e:
                logger.error("Cluster::daemon: Failed to load PF rules : {}".format(str(e)))

            time.sleep(5)
            logger.info("Cluster::daemon: Trying to resume...")
            error = True
            this_node = None
            continue

    # Ask the jobs to terminate.
    monitor_job.stop()

    logger.info("Vultured stopped.")
