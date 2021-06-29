#!/usr/bin/python
# -*- coding: utf-8 -*-
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
__author__ = "Kevin Guillemot"
__credits__ = []
__license__ = "GPLv3"
__version__ = "3.0.0"
__maintainer__ = "Vulture Project"
__email__ = "contact@vultureproject.org"
__doc__ = 'REDIS interaction classes'


# Django system imports
from django.conf                    import settings
from django.utils.crypto            import get_random_string

# Django project imports
from authentication.base_repository import BaseRepository
from authentication.learning_profiles.models import LearningProfile

# Required exceptions imports
from .exceptions                     import TokenNotFoundError, REDISWriteError
from redis                          import Redis, ConnectionError as RedisConnectionError, ResponseError as RedisResponseError

# Extern modules imports
from hashlib                        import sha1
import json
from copy import deepcopy

# Logger configuration
import logging
logging.config.dictConfig(settings.LOG_SETTINGS)
logger = logging.getLogger('portal_authentication')


# Global variables
default_timeout = 900




class REDISSession(object):
    def __init__(self, redis_handler, key, *args, **kwargs):
        self.handler = redis_handler
        self.key     = key
        self.keys    = self.handler.hgetall(self.key)
        # Force-update kwargs in keys
        for k,v in kwargs.items():
            if v is not None:
                self.keys[k] = v

    def __setitem__(self, key, value):
        self.keys[key] = value
        # You must call write_in_redis after this

    def __getitem__(self, key):
        return self.keys.get(key)

    def write_in_redis(self, timeout):
        # Do NOT write user_infos in Redis, it has already be done  in set_user_infos
        if self.handler.hmset(self.key, {k:v for k,v in self.keys.items() if not k.startswith("user_infos_") and v is not None}):
            if self.handler.ttl(self.key) < timeout:
                return self.handler.expire(self.key, timeout)
            return True
        else:
            return False

    def set_in_redis(self, key, value, timeout=0):
        self.handler.set(key, value)
        if timeout:
            self.handler.expire(key, timeout)

    def delete_in_redis(self, key):
        logger.error(f"deleting {key} in redis")
        return self.handler.delete(key)


class REDISAppSession(REDISSession):
    """ This class is in charge of managing Redis Session for anonymous & authenticated users
    """

    def __init__(self, redis_handler, **kwargs):
        """ Retrieve info from redis, with the given token

        WE CAN FIND 2 KIND OF STRUCTURE in a REDISSession:
            1) An "app_cookie" stored in Redis under the "token" key
                [ token | app_cookie ]

                -   The "token" is dynamically generated by mod_vulture.
                -   The "token" value is transmitted to portal in the URL, by mod_vulture (via a variable, 'server_public_token' defined in the GUI)
                -   The "app_cookie" is used to identified the user's session on the App and is also generated by mod_vulture

                => When redirected to Vulture Portal, the user won't send any cookie because portal may be in another domain
                    - That's why we use the token in URL
                    - With that token we can find the cookie_value of the user's session in Redis
                    - We will then be able to update the status (authentified=1) for this session

                => This entry in Redis is ephemeral: Once processed by portal, the entry is useless, because the User
                will send its "app_cookie" in every request to mod_vulture, and mod_vulture won't have to redirect to portal
                because in REDIS there is login status associated to the app_cookie

            2) An "Application session" stored in Redis under the "app_cookie" key
                [ app_cookie | login | cn | application_id | url | authenticated | headers ]

                - The session is first created by mod_vulture (authenticated = 0)
                - The session is then updated by portal if user logs in (authenticated = 1)

        :param redis_handler: an Handler to the Redis Server, previously opened with REDISBase (=> redis.Redis())
        :param kwargs:
        :return:
        """
        """ Simple use token, that points to the application's hash in REDIS """

        """ Get the application's hash in REDIS """
        app_cookie = kwargs.get('cookie', None)

        self.default_timeout = default_timeout
        super(REDISAppSession, self).__init__(redis_handler, app_cookie)

        if app_cookie is None:
            raise TokenNotFoundError("REDISSession: No session found for cookie " + str(app_cookie))

        try:
            assert( self.keys['authenticated'] )
        except (AssertionError, KeyError, TypeError) as e:
            """ Delete bad cookie Session """
            self.handler.delete(str(app_cookie))

            raise TokenNotFoundError("REDISAppSession: No user session found for token '{}'".format(self.key))

    def is_authenticated(self):
        return (self.handler.hget(self.key, 'authenticated') == "1")

    def get_otp_retries(self):
        return self.handler.hget(self.key, 'otp_retries')


    def deauthenticate(self):
        self.keys['authenticated'] = 0
        self.handler.hset(self.key, 'authenticated', 0)
        self.keys.pop('otp_retries', None)
        self.handler.hdel(self.key, 'otp_retries')


    def setHeader(self, headers):
        """
        :param app_session: The Application's cookie value
        :param username: The username associated to the session
        :param headers: A string that needs to be send as headers by mod_vulture ("test1:test2\r\nabcd1:abcd2\r\n")
        :return: self.handler.hset
        """

        """ Update application hashmap """
        self.keys['headers'] = headers
        self.handler.hset(str(self.key), 'headers', headers)
        return True


    def setKrb5Infos(self, username, krb5service, backend_id):
        """
        :param app_session: The Application's cookie value
        :param username: The username associated to the session
        :param krb5service: The kerberos service of the requested app
        :param backend_id: The backend id used to authenticate the user
        :return: self.handler.hset
        """

        """ Update application hashmap """
        self.keys['login'] = username

        """ add 'krb5ccname' and 'krb5service' keys to Redis """
        krb5ccname               = "FILE:/tmp/krb5cc_" + sha1(str(backend_id) + str(username)).hexdigest()
        self.keys['krb5ccname']  = krb5ccname
        self.keys['krb5service'] = "HTTP@" + krb5service

        if not self.handler.hmset(self.key, self.keys):
            raise REDISWriteError("REDISAppSession::setKrb5Infos: Unable to write krb5 infos in REDIS")
        return True


    def register_authentication(self, app_id, username, timeout):
        """
        Add an application in the user's session, and set authenticated to true

        Synoptic:
            o Delete token | app_cookie in Redis, this is useless now
            o Update hashmap 'single application': Define 'login', define 'cn' and set authenticated=1

        :return: self.key or raise
        """

        """ Update application hashmap """
        self.keys['authenticated']  = 1
        self.keys['login']          = username
        self.keys['application_id'] = str(app_id)
        self.keys['otp_retries']    = 0

        if not self.write_in_redis(timeout):
            raise REDISWriteError("REDISAppSession::register_authentication: Unable to write authentications infos in REDIS")

        return self.key


    def destroy(self):
        self.handler.delete(self.key)



class REDISPortalSession(REDISSession):
    """  Here we manage a  "Portal session" stored in Redis under the "portal_cookie" key
                [ portal_cookie | url_app_x | backend_app_x | login_backend_x | password_backend_x | backend_x ]

                - This is used to know on which backend the user is already authenticated
                - This is also used to retrieve user's password and login for SSO Autologon

    """

    def __init__(self, redis_handler, portal_cookie, *args, **kwargs):
        super().__init__(redis_handler, portal_cookie or get_random_string(64), *args, **kwargs)

    def destroy(self):
        """ Remove the current portal session from Redis """
        try:
            # Remove all potential related keys in the form <key>_*
            for key, value in self.keys.items():
                if "_" not in key and value == "1":
                    self.delete_in_redis(f"{self.key}_{key}")
            for key, value in self.keys.items():
                if key.startswith("portal_") and value == "1":
                    self.delete_in_redis(f"{self.key}_{key}")
            return self.handler.delete(self.key)
        except:
            logger.info("REDISPortalSession: portal_session '{}' cannot be destroyed".format(self.key))
            pass

    """ Verify in REDIS if the portal_cookie is present """
    def exists(self):
        a = self.handler.hgetall(self.key)
        if a:
            return True
        return None

    def get_otp_key(self):
        return self.handler.hget(self.key, 'otp')

    def set_otp_info(self, otp_info):
        self.handler.hset(str(self.key), 'otp', otp_info)

    def get_login(self, backend_id):
        return self.handler.hget(self.key, f'login_{backend_id}')

    def authenticated_app(self, workflow_id):
        return self.handler.get(f"{self.key}_{workflow_id}") == "1"

    def authenticated_backend(self, backend_id):
        return str(self.handler.hget(self.key, f"auth_backend_{backend_id}")) == "1"

    def is_double_authenticated(self, otp_backend_id):
        return str(self.handler.hget(self.key, 'doubleauthenticated_{}'.format(str(otp_backend_id)))) == "1"

    def get_oauth2_token(self, backend_id):
        return self.handler.hget(self.key, f'oauth2_{backend_id}')

    def set_oauth2_token(self, backend_id, oauth2_token):
        self.keys[f'oauth2_{backend_id}'] = oauth2_token
        return self.handler.hset(self.key, f'oauth2_{backend_id}', oauth2_token)

    def get_auth_backend(self, workflow_id):
        return self.handler.hget(self.key, f'backend_{workflow_id}')

    def get_user_infos(self, backend_id):
        return json.loads(self.handler.hget(self.key, f'user_infos_{backend_id}') or "{}")

    def set_user_infos(self, backend_id, user_infos):
        self.keys[f'user_infos_{backend_id}'] = user_infos
        return self.handler.hset(self.key, f'user_infos_{backend_id}', json.dumps(user_infos or {}))

    def delete_key(self, key):
        # Remove key in keys attribute to prevent cache re-use
        # Do not raise if key does not exist
        self.keys.pop(key, None)
        # And remove key in Redis
        return self.handler.hdel(self.key, key)

    def retrieve_captcha(self, workflow_id):
        return self.handler.hget(self.key, f'captcha_{workflow_id}')

    def register_captcha(self, workflow_id):
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        secret_key = get_random_string(6, chars)
        self.keys['captcha_{}'.format(workflow_id)] = secret_key
        self.handler.hset(self.key, 'captcha_{}'.format(workflow_id), secret_key)
        return secret_key


    def getAutologonPassword(self, app_id, backend, username):
        """ Retrieve encrypted password in REDIS, decrypt it and return it plain text """
        # Get the encrypted password's value for the current backend
        p = self.handler.hget(self.key, 'password_'+backend)
        if not p:
            return None

        # And decrypt it with the app_id and username given
        pwd = LearningProfile()
        decrypted_pass = pwd.get_data(p, app_id, backend, username, 'vlt_autologon_password')
        return decrypted_pass


    """ Update encrypted password in REDIS """
    def setAutologonPassword(self, app_id, app_name, backend_id, username, password):
        pwd = LearningProfile()
        p = pwd.set_data(app_id, app_name, backend_id, BaseRepository.objects.get(pk=backend_id).name, username,
                         'vlt_autologon_password', password)
        self.keys[f'password_{backend_id}'] = p

    def getData(self):
        """ Return portal_session or None if portal session does not exist """
        if self.key is None:
            return None
        return self.handler.hgetall(self.key)

    def increment_otp_retries(self, otp_repo_id):
        otp_retries = int( self.handler.hget(self.key, f"otp_retries_{otp_repo_id}" ) or '0') + 1
        self.keys[f"otp_retries_{otp_repo_id}"] = otp_retries
        self.handler.hset(self.key, f"otp_retries_{otp_repo_id}", otp_retries)
        return otp_retries

    def deauthenticate(self, workflow_id, backend_id, timeout):
        # TODO : otp_retries_{otp_backend_id}
        self.keys.pop('otp_retries', None)
        self.keys[workflow_id] = 0
        self.keys[f'auth_backend_{backend_id}'] = 0
        self.keys.pop(f'backend_{workflow_id}', None)
        self.keys.pop(f'login_{backend_id}', None)
        self.keys.pop(f'oauth2_{backend_id}', None)
        self.keys.pop(f'app_id_{backend_id}', None)

        # Remove
        self.delete_in_redis(f"{self.key}_{workflow_id}")

        if not self.write_in_redis(timeout or self.default_timeout):
            raise REDISWriteError("REDISPortalSession::register_authentication: Unable to write authentication infos "
                                  "in REDIS")

    def deauthenticate_app(self, app_id, timeout):
        self.keys[str(app_id)] = 0
        self.keys.pop(f"backend_{app_id}", None)
        self.keys.pop(f"url_{app_id}", None)
        self.delete_in_redis(f"{self.key}_{app_id}")
        self.write_in_redis(timeout)

    def register_authentication(self, app_id, app_name, backend_id, dbauthentication_required, username, password,
                                oauth2_token, authentication_datas, timeout):
        if dbauthentication_required:
            self.keys[str(app_id)] = 0
        else:
            self.keys[str(app_id)] = 1
        # The user is authenticated on repository
        self.keys[f"auth_backend_{backend_id}"] = 1
        #self.keys['url_'+app_id]  = url
        self.keys[f"backend_{app_id}"] = str(backend_id)
        self.keys[f"login_{backend_id}"] = username
        if oauth2_token:
            self.keys[f"oauth2_{backend_id}"] = str(oauth2_token)
        self.keys[f"app_id_{backend_id}"] = str(app_id)

        # WARNING : THE KEYS ARE NOT INITIALIZED ANYMORE !
        # self.keys['otp']        = None
        # self.keys['authy_id']   = None
        # self.keys['user_phone'] = None
        # self.keys['user_mail']  = None

        """ Try to retrieve user phone from authentication_results """
        #self.keys['user_phone'] = authentication_datas.get('user_phone', 'N/A')
        #self.keys['user_email'] = authentication_datas.get('user_email', 'N/A')
        # Save all user infos
        self.set_user_infos(backend_id, authentication_datas)

        # Save additional related key for Darwin Session quick verification
        self.set_in_redis(f"{self.key}_{app_id}", "1", timeout or self.default_timeout)

        if password:
            # Encrypt the password with the application id and user login and store it in portal session
            self.setAutologonPassword(app_id, app_name, backend_id, username, password)

        if not self.write_in_redis(timeout or self.default_timeout):
            raise REDISWriteError("REDISPortalSession::register_authentication: Unable to write authentication infos "
                                  "in REDIS")

        return self.key

    def register_doubleauthentication(self, app_id, otp_backend_id):
        self.keys[str(app_id)] = 1
        self.handler.hset(self.key, str(app_id), 1)
        backend_id = self.keys[f"backend_{app_id}"]
        self.keys[f"auth_backend_{backend_id}"] = 1
        self.handler.hset(self.key, f"auth_backend_{backend_id}", "1")
        self.keys[f"doubleauthenticated_{otp_backend_id}"] = "1"
        self.handler.hset(self.key, f"doubleauthenticated_{otp_backend_id}", "1")

    def register_sso(self, timeout, backend_id, app_id, otp_repo_id, username, oauth2_token):
        if not otp_repo_id or (otp_repo_id and self.is_double_authenticated(otp_repo_id)):
            self.keys[str(app_id)] = 1

        self.keys[f"auth_backend_{backend_id}"] = 1
        self.keys[f"backend_{app_id}"] = backend_id
        self.keys[f"login_{backend_id}"] = username
        if oauth2_token:
            self.keys[f"oauth2_{backend_id}"] = oauth2_token

        # Save additional related key for Darwin Session quick verification
        self.set_in_redis(f"{self.key}_{app_id}", "1", timeout or self.default_timeout)

        if not self.write_in_redis(timeout or self.default_timeout):
            raise REDISWriteError("REDISPortalSession::register_sso: Unable to write SSO infos in REDIS")

        return self.key


    def get_auth_backends(self):
        max_loop = 50 # Number max of applications in SSO ?
        result = dict()
        tmp = self.handler.hscan(self.key, 0, "backend_*")
        for key, item in tmp[1].items():
            result[key] = item
        cpt = tmp[0]

        cpt_loop = 0
        while cpt != 0 and cpt_loop < max_loop:
            tmp = self.handler.hscan(self.key, cpt, "backend_*")
            for key,item in tmp[1].items():
                result[key] = item
            cpt = tmp[0]
            cpt_loop += 1

        return result

    def __str__(self):
        return json.dumps(self.keys)


class REDISOauth2Session(REDISSession):
    def __init__(self, redis_handler, oauth2_token):
        super().__init__(redis_handler, oauth2_token)
        # Interpret
        if "scope" in self.keys:
            self.keys['scope'] = json.loads(self.keys['scope'])
        else:
            self.keys['scope'] = {}

    def write_in_redis(self, timeout):
        backup_scope = deepcopy(self.keys['scope'])
        # Do not insert json into Redis
        self.keys['scope'] = json.dumps(self.keys['scope'])
        ret = super().write_in_redis(timeout)
        # Restore dict in case of re-use
        self.keys['scope'] = backup_scope

        return ret

    def register_authentication(self, repo_id, oauth2_data, timeout):
        data = {
            'token_ttl': timeout,
            'scope': oauth2_data,
            'repo': str(repo_id)
        }
        if not self.keys:
            self.keys = data
        else:
            if not self.keys.get('scope'):
                self.keys['scope'] = {}
            if not self.keys.get('token_ttl'):
                self.keys['token_ttl'] = timeout
            if not self.keys.get('repo'):
                self.keys['repo'] = repo_id
            for key,item in oauth2_data.items():
                self.keys['scope'][key] = item
        if not self.write_in_redis(timeout):
            logger.error("REDIS::register_authentication: Error while writing portal_session in Redis")
            raise REDISWriteError("REDISOauth2Session::register_authentication: Unable to write Oauth2 infos in REDIS")
        return self.key


class RedisOpenIDSession(REDISSession):
    def __init__(self, redis_handler, openid_token):
        super().__init__(redis_handler, openid_token)

    def register(self, oauth2_token, **kwargs):
        self.keys = kwargs
        self.keys['access_token'] = oauth2_token

        # This is a temporary token, used for redirection and access_token retrieve
        if not self.write_in_redis(30):
            logger.error("REDIS::register_authentication: Error while writing portal_session in Redis")
            raise REDISWriteError("REDISOauth2Session::register_authentication: Unable to write Oauth2 infos in REDIS")

        return self.key


class REDISBase(object):
    """Base class for database wrapper
    """

    ip = settings.REDISIP
    port = settings.REDISPORT
    r = None
    logger = logging.getLogger('redis_events')

    def __init__(self):
        super(REDISBase, self).__init__()

        try:
            #self.r = Redis(host=self.ip, port=self.port, db=0)
            self.r = Redis(unix_socket_path='/var/sockets/redis/redis.sock', db=0, decode_responses=True)
            self.r.info()
        except Exception as e:
            self.logger.info("REDISBase: REDIS connexion issue")
            self.logger.exception(e)
            raise RedisConnectionError(e)


    # Write function : need master Redis
    def delete(self, key):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.delete(key)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.delete(key)
        return result


    # Write function : need master Redis
    def hdel(self, hash, key):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.hdel(hash, key)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.hdel(hash, key)
        return result


    # Write function : need master Redis
    def set(self, key, value):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.set(key, value)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.set(key, value)
        return result


    # Retrieve function : no need master
    def get(self, key):
        try:
            v = self.r.get(key)
        except RedisResponseError as e:
            return None
        except Exception as e:
            self.logger.exception(e)
            return None
        return v


    # Retrieve function : no need master
    def hget(self, hash, key):
        try:
            v = self.r.hget(hash, key)
        except Exception as e:
            self.logger.exception(e)
            return None
        return v


    # Write function : need master Redis
    def expire(self, key, ttl):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.expire(key, ttl)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.expire(key, ttl)
        return result


    # Retrieve ttl function : no need master
    def ttl(self, key):
        try:
            v = self.r.ttl(key)
        except RedisResponseError as e:
            return None
        except Exception as e:
            self.logger.exception(e)
            return None
        return v


    # Write function : need master Redis
    def hset(self, hash, key, value):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.hset(hash, key, value)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.hset(hash, key, value)
        return result


    # Write function : need master Redis
    def hmset(self, hash, mapping):
        result = None
        # Get role of current cluster
        cluster_info = self.r.info()
        # If current cluster isn't master: get the master
        if "master" not in cluster_info['role']:
            # backup current cluster
            r_backup = self.r
            # And connect to master
            try:
                self.r = Redis(host=cluster_info['master_host'], port=cluster_info['master_port'], db=0)
                result = self.r.hmset(hash, mapping)
            except Exception as e:
                self.logger.info("REDISSession: Redis connexion issue")
                self.logger.exception(e)
                result = None
            # Finally restore the backuped cluster
            self.r = r_backup
        else:  # If current cluster is Master
            result = self.r.hmset(hash, mapping)
        return result


    # Retrieve function : no need master
    def hgetall(self, hash):
        try:
            v = self.r.hgetall(hash)
        except Exception as e:
            self.logger.exception(e)
            return None
        return v


    def hscan(self, hash, cursor=0, match=None, count=None):
        return self.r.hscan(hash, cursor, match, count)


    def keys(self, pattern):
        return self.r.keys(pattern)