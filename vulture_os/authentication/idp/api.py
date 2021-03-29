#!/home/vlt-os/env/bin/python
"""This file is part of Vulture OS.

Vulture OS is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Vulture OS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Vulture OS.  If not, see http://www.gnu.org/licenses/.
"""
__author__ = "Olivier de Régis"
__credits__ = []
__license__ = "GPLv3"
__version__ = "3.0.0"
__maintainer__ = "Vulture OS"
__email__ = "contact@vultureproject.org"
__doc__ = 'IDP API'

import logging
from django.views import View
from django.conf import settings
from authentication import ldap
from authentication.ldap import tools
from django.http import JsonResponse
from gui.decorators.apicall import api_need_key
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext_lazy as _
from authentication.user_portal.models import UserAuthentication

logging.config.dictConfig(settings.LOG_SETTINGS)
logger = logging.getLogger('api')

def get_repo(portal):
    ldap_repo = None
    for repo in portal.repositories.all():
        if repo.subtype == "LDAP":
            ldap_repo = repo.get_daughter()
            break

    if not ldap_repo:
        # The portal does not have a LDAP repository
        raise UserAuthentication.DoesNotExist()

    return ldap_repo


@method_decorator(csrf_exempt, name="dispatch")
class IDPApiView(View):
    @api_need_key("cluster_api_key")
    def get(self, request, object_id):
        try:
            portal = UserAuthentication.objects.get(pk=object_id)
            ldap_repo = get_repo(portal)

            object_type = request.GET["object_type"].lower()
            if object_type not in ("groups", "users", "search"):
                raise KeyError()

            if object_type == "groups":
                data = tools.get_groups(ldap_repo)
                groups = [elem[ldap_repo.group_attr][0] for elem in data]
                return JsonResponse({
                    "data": groups
                })
            
            elif object_type == "users":
                group_name = request.GET.get('group_name')
                users = tools.get_users(ldap_repo, group_name)
                return JsonResponse({
                    "data": users
                })

            elif object_type == "search":
                search_str = request.GET['search']
                data = tools.search_users(ldap_repo, search_str)
                return JsonResponse({
                    "data": data
                })

        except KeyError as err:
            logger.error(err)
            return JsonResponse({
                "status": False,
                "error": _("Invalid call")
            }, status=400)

        except UserAuthentication.DoesNotExist:
            return JsonResponse({
                "status": False,
                "error": _("Portal does not exist")
            }, status=404)
        except Exception as err:
            logger.critical(err, exc_info=1)
            if settings.DEV_MODE:
                raise

            return JsonResponse({
                "status": False,
                "error": str(err)
            }, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class IDPApiUserView(View):
    @api_need_key('cluster_api_key')
    def post(self, request, object_id):
        try:
            portal = UserAuthentication.objects.get(pk=object_id)
            ldap_repo = get_repo(portal)

            user = {
                ldap_repo.user_attr: request.JSON['username'],
                ldap_repo.user_groups_attr: request.JSON.get('group')
            }

            attrs = {}

            try:
                attrs[ldap_repo.user_email_attr] = request.JSON['email']
            except  KeyError:
                pass

            try:
                attrs[ldap_repo.user_account_locked_attr] = request.JSON['is_locked']
            except KeyError:
                pass
                
            try:
                attrs[ldap_repo.user_change_password_attr] = request.JSON['need_change_password']
            except KeyError:
                pass

            try:
                attrs[ldap_repo.user_mobile_attr] = request.JSON['mobile']
            except KeyError:
                pass

            try:
                attrs[ldap_repo.user_smartcardid_attr] = request.JSON['smartcardid']
            except KeyError:
                pass

            try:
                attrs[ldap_repo.user_type_attr] = request.JSON['user_type']
            except KeyError:
                pass
            
            try:
                attrs[ldap_repo.user_firstname_attr] = request.JSON['first_name']
            except KeyError:
                pass

            try:
                attrs[ldap_repo.user_lastname_attr] = request.JSON['last_name']
            except KeyError:
                pass

            try:
                attrs[ldap_repo.user_authorisation_attr] = request.JSON['authorisations']
            except KeyError:
                pass

            group_name = user[ldap_repo.user_groups_attr]
            ldap_response, user_id = tools.create_user(ldap_repo, group_name, user[ldap_repo.user_attr], request.JSON.get('userPassword'), attrs)

            return JsonResponse({
                "status": True,
                "user_id": user_id
            }, status=201)
        except KeyError as err:
            logger.debug(err)
            return JsonResponse({
                "status": False,
                "error": _("Invalid call")
            }, status=400)

        except UserAuthentication.DoesNotExist:
            return JsonResponse({
                "status": False,
                "error": _("Portal does not exist")
            }, status=404)
        except Exception as err:
            logger.critical(err, exc_info=1)
            if settings.DEV_MODE:
                raise

            return JsonResponse({
                "status": False,
                "error": str(err)
            }, status=500)

    @api_need_key('cluster_api_key')
    def put(self, request, object_id):
        try:
            portal = UserAuthentication.objects.get(pk=object_id)
            ldap_repo = get_repo(portal)

            dn = request.JSON['id']
            user_name = request.JSON['username']
            group_name = request.JSON.get('group')

            attrs = {
                ldap_repo.user_attr: [user_name]
            }

            if ldap_repo.user_email_attr:
                attrs[ldap_repo.user_email_attr] = request.JSON.get('email')
            
            if ldap_repo.user_account_locked_attr:
                attrs[ldap_repo.user_account_locked_attr] = request.JSON.get('is_locked')
            
            if ldap_repo.user_change_password_attr:
                attrs[ldap_repo.user_change_password_attr] = request.JSON.get('need_change_password')
            
            if ldap_repo.user_mobile_attr:
                attrs[ldap_repo.user_mobile_attr] = request.JSON.get('mobile')
            
            if ldap_repo.user_smartcardid_attr:
                attrs[ldap_repo.user_smartcardid_attr] = request.JSON.get('smartcardid')
            
            if ldap_repo.user_type_attr:
                attrs[ldap_repo.user_type_attr] = request.JSON.get('user_type')

            if ldap_repo.user_firstname_attr:
                attrs[ldap_repo.user_firstname_attr] = request.JSON.get('first_name')

            if ldap_repo.user_lastname_attr:
                attrs[ldap_repo.user_lastname_attr] = request.JSON.get('last_name')

            if ldap_repo.user_authorisation_attr:
                attrs[ldap_repo.user_authorisation_attr] = request.JSON.get('authorisations')

            status, user_dn = tools.update_user(ldap_repo, group_name, dn, user_name, attrs, request.JSON.get('userPassword'))
            if status is False:
                return JsonResponse({
                    "status": False,
                    "error": _("User not found")
                }, status=404)

            return JsonResponse({
                "status": True,
                "user_id": user_dn
            })
        except KeyError as err:
            logger.debug(err)
            return JsonResponse({
                "status": False,
                "error": _("Invalid call")
            }, status=400)

        except UserAuthentication.DoesNotExist:
            return JsonResponse({
                "status": False,
                "error": _("Portal does not exist")
            }, status=404)
        except Exception as err:
            logger.critical(err, exc_info=1)
            if settings.DEV_MODE:
                raise

            return JsonResponse({
                "status": False,
                "error": str(err)
            }, status=500)

    @api_need_key('cluster_api_key')
    def delete(self, request, object_id):
        try:
            portal = UserAuthentication.objects.get(pk=object_id)
            ldap_repo = get_repo(portal)

            user_dn = request.JSON['id']
            group_name = request.JSON.get('group')

            status, user_id = tools.delete_user(ldap_repo, group_name, user_dn)
            if status is False:
                return JsonResponse({
                    "status": False,
                    "error": _("User not found")
                }, status=404)

            return JsonResponse({
                "status": True,
                "user_id": user_id
            })
        except KeyError as err:
            logger.error(err)
            return JsonResponse({
                "status": False,
                "error": _("Invalid call")
            }, status=400)

        except UserAuthentication.DoesNotExist:
            return JsonResponse({
                "status": False,
                "error": _("Portal does not exist")
            }, status=404)
        except Exception as err:
            logger.critical(err, exc_info=1)
            if settings.DEV_MODE:
                raise

            return JsonResponse({
                "status": False,
                "error": str(err)
            }, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class IDPApiGroupView(View):
    @api_need_key("cluster_api_key")
    def post(self, request, object_id):
        try:
            portal = UserAuthentication.objects.get(pk=object_id)
            ldap_repo = get_repo(portal)

            group_name = request.JSON['group_name']
            members = request.JSON['member']
            status, ldap_response = tools.create_group(ldap_repo, group_name, members)
            if not status:
                return JsonResponse({
                    "status": False,
                    "error": ldap_response
                }, status=400)
            
            return JsonResponse({
                "status": True
            }, status=201)

        except KeyError as err:
            logger.debug(err)
            return JsonResponse({
                "status": False,
                "error": _("Invalid call")
            }, status=400)

        except UserAuthentication.DoesNotExist:
            return JsonResponse({
                "status": False,
                "error": _("Portal does not exist")
            }, status=404)
        except Exception as err:
            logger.critical(err, exc_info=1)
            if settings.DEV_MODE:
                raise

            return JsonResponse({
                "status": False,
                "error": str(err)
            }, status=500)
