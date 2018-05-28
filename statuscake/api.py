import time

import requests
from requests.adapters import HTTPAdapter
import six
from six.moves.urllib.parse import urlencode

from .exceptions import StatusCakeError, StatusCakeAuthError, StatusCakeNotLinkedError, StatusCakeFieldMissingError, StatusCakeFieldError, StatusCakeResponseError


def to_comma_list(value):
    if isinstance(value, (list, tuple, set, frozenset)):
        value = ','.join(value)
    return value


def to_int(value):
    if isinstance(value, bool):
        value = int(value)
    return value


class StatusCake(object):
    URL_LOCATIONS = "https://app.statuscake.com/API/Locations/json"
    URL_ALERT = "https://app.statuscake.com/API/Alerts/?TestID=%s"
    URL_ALL_GROUPS = "https://app.statuscake.com/API/ContactGroups/"
    URL_UPDATE_GROUP = "https://app.statuscake.com/API/ContactGroups/Update/"
    URL_DELETE_GROUP = URL_UPDATE_GROUP + "?ContactID=%s"
    URL_ALL_TESTS = "https://app.statuscake.com/API/Tests/"
    URL_DETAILS_TEST = "https://app.statuscake.com/API/Tests/Details/?TestID=%s"
    URL_UPDATE_TEST = "https://app.statuscake.com/API/Tests/Update"
    URL_PERIODS = "https://app.statuscake.com/API/Tests/Periods/?TestID=%s"
    URL_CHECKS = "https://app.statuscake.com/API/Tests/Checks/?TestID=%s"
    URL_SSL = "https://app.statuscake.com/API/SSL/"
    URL_UPDATE_SSL = "https://app.statuscake.com/API/SSL/Update"
    URL_PAGE_SPEED = "https://app.statuscake.com/API/Pagespeed"

    CONTACT_GROUP_FIELDS = {
        'GroupName': (six.string_types, None, None),
        'DesktopAlert': (int, (0, 1), None),
        'Email': (six.string_types, None, to_comma_list),
        'Boxcat': (six.string_types, None, None),
        'Pushover': (six.string_types, None, None),
        'PingURL': (six.string_types, None, None),
        'Mobile': (six.string_types, None, to_comma_list),
        'ContactID': (int, None, None),
    }

    SSL_FIELDS = {
        'domain': (six.string_types, None, None),
        'checkrate': (int, (300, 600, 2800, 3600, 86400, 2073600), None),
        'contact_groups': (six.string_types, None, to_comma_list),
        'alert_at': (six.string_types, None, None),
        'alert_expiray': (bool, None, None),
        'alert_reminder': (bool, None, None),
        'alert_broken': (bool, None, None)
    }

    TESTS_FIELDS = {
        'TestID': (int, None, None),
        'Paused': (int, (0, 1), to_int),
        'WebsiteName': (six.string_types, None, None),
        'WebsiteURL': (six.string_types, None, None),
        'Port': (int, None, None),
        'NodeLocations': (six.string_types, None, to_comma_list),
        'Timeout': (int, range(5, 101), None),
        'PingURL': (six.string_types, None, None),
        'Confirmation': (int, range(0, 11), None),
        'CheckRate': (int, range(0, 24001), None),
        'BasicUser': (six.string_types, None, None),
        'BasicPass': (six.string_types, None, None),
        'Public': (int, (0, 1), None),
        'LogoImage': (six.string_types, None, None),
        'Branding': (int, (0, 1), None),
        'WebsiteHost': (six.string_types, None, None),
        'Virus': (int, (0, 1), None),
        'FindString': (six.string_types, None, None),
        'DoNotFind': (int, (0, 1), None),
        'TestType': (six.string_types, ("HTTP", "TCP", "PING", "PUSH"), None),
        'ContactGroup': (six.string_types, None, to_comma_list),
        'RealBrowser': (int, (0, 1), None),
        'TriggerRate': (int, range(0, 61), None),
        'TestTags': (six.string_types, None, to_comma_list),
        'FinalEndpoint': (six.string_types, None, None),
        'PostRaw': (six.string_types, None, None),
        'EnableSSLAlert': (int, (0, 1), None)
    }

    def __init__(self, api_key, api_user, timeout=10):
        self._api_key = api_key
        self._api_user = api_user
        self.timeout = 10

        self.session = requests.Session()
        self.session.mount('https://www.statuscake.com', HTTPAdapter(max_retries=5))

    def _request(self, method, url, data=None, auth_headers=True, check_errors=True, **kwargs):
        headers = {}
        if auth_headers:
            headers.update({
                'API': self._api_key,
                'Username': self._api_user,
            })

        if isinstance(data, dict):
            data = urlencode(data)

        kwargs.setdefault('timeout', self.timeout)
        print_json = kwargs.pop('print_json', False)
        print_raw = kwargs.pop('print_raw', False)
        response = getattr(self.session, method)(url, headers=headers, data=data, **kwargs)
        if print_raw:
            print(response.text)
        if print_json:
            print(response.json())
        if check_errors:
            json_resp = response.json()
            if isinstance(json_resp, dict) and (json_resp.get('Success', True) is False or json_resp.get('Error', None) is not None):
                errno = json_resp.get('ErrNo', -1)
                error_message = json_resp.get('Error')
                if not error_message:
                    error_message = json_resp.get('Message')
                if errno == 0:
                    raise StatusCakeAuthError(error_message or 'Authentication Failed')
                elif errno == 1:
                    raise StatusCakeNotLinkedError(error_message or 'Authentication Failed')
                raise StatusCakeResponseError(error_message or 'API Call Failed')
        return response

    def _check_fields(self, data, check_map):
        for field_name, (field_type, field_values, field_conv) in six.iteritems(check_map):
            if field_name not in data:
                continue
            if field_conv:
                try:
                    data[field_name] = field_conv(data[field_name])
                except TypeError as exc:
                    raise StatusCakeFieldError("Field %s: %s" % (field_name, str(exc)))
            if not isinstance(data[field_name], field_type):
                raise StatusCakeFieldError("Field %s must be of type %s" % (field_name, field_type))
            if field_values is not None and data[field_name] not in field_values:
                raise StatusCakeFieldError("Field %s value %s does not match one of: %s" % (field_name, field_type, field_values))

    def get_node_locations(self, **kwargs):
        if hasattr(self, '_location_cache_timeout') and hasattr(self, '_location_cache'):
            if self._location_cache_timeout > time.time():
                return self._location_cache
        locations = self._request('get', self.URL_LOCATIONS, auth_headers=False, check_errors=False, **kwargs).json()
        self._location_cache_timeout = time.time() + 900
        self._location_cache = locations
        return locations

    def get_contact_groups(self, **kwargs):
        return self._request('get', self.URL_ALL_GROUPS, **kwargs).json()

    def insert_contact_group(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'GroupName' not in data:
            raise StatusCakeFieldMissingError("GroupName missing")
        self._check_fields(data, self.CONTACT_GROUP_FIELDS)
        return self._request('put', self.URL_UPDATE_GROUP, data=data, **kwargs).json()

    def update_contact_group(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'ContactID' not in data:
            raise StatusCakeFieldMissingError("ContactID missing")
        self._check_fields(data, self.CONTACT_GROUP_FIELDS)
        return self._request('put', self.URL_UPDATE_GROUP, data=data, **kwargs).json()

    def delete_contact_group(self, contact_id, **kwargs):
        return self._request('delete', self.URL_DELETE_GROUP % contact_id, **kwargs).json()

    def get_alert(self, test_id, **kwargs):
        return self._request('get', self.URL_ALERT % test_id, **kwargs).json()

    def get_all_tests(self, **kwargs):
        return self._request('get', self.URL_ALL_TESTS, **kwargs).json()

    def get_all_ssl(self, **kwargs):
        return self._request('get', self.URL_SSL, **kwargs).json()

    def get_details_test(self, test_id, **kwargs):
        return self._request('get', self.URL_DETAILS_TEST % test_id, **kwargs).json()

    def get_periods(self, test_id, **kwargs):
        return self._request('get', self.URL_PERIODS % test_id, **kwargs).json()

    def get_checks(self, test_id, **kwargs):
        # pass optional parameters like params = {'Fields': 'location,performance'}
        return self._request('get', self.URL_CHECKS % test_id, **kwargs).json()

    def delete_test(self, test_id, **kwargs):
        return self._request('delete', self.URL_DETAILS_TEST % test_id, **kwargs).json()

    def insert_ssl(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'domain' not in data:
            raise StatusCakeFieldMissingError("domain missing")
        if 'checkrate' not in data:
            data['checkrate'] = 3600
        if 'contact_groups' not in data:
            raise StatusCakeFieldMissingError("contact_groups missing")
        if 'alert_at' not in data:
            data['alert_at'] = '1,7,30'
        if 'alert_expiry' not in data:
            data['alert_expiry'] = True
        if 'alert_reminder' not in data:
            data['alert_reminder'] = True
        if 'alert_broken' not in data:
            data['alert_broken'] = True
        self._check_fields(data, self.SSL_FIELDS)
        return self._request('put', self.URL_UPDATE_SSL, data=data, **kwargs).json()

    def update_ssl(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'id' not in data:
            raise StatusCakeFieldMissingError("id missing")
        self._check_fields(data, self.SSL_FIELDS)
        return self._request('put', self.URL_UPDATE_SSL, data=data, **kwargs).json()

    def delete_ssl(self, id, **kwargs):
        return self._request('delete', self.URL_UPDATE_SSL, data={'id': id}, **kwargs).json()

    def insert_test(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'WebsiteName' not in data:
            raise StatusCakeFieldMissingError("WebsiteName missing")
        if 'WebsiteURL' not in data:
            raise StatusCakeFieldMissingError("WebsiteURL missing")
        if 'TestType' not in data:
            raise StatusCakeFieldMissingError("TestType missing")
        if 'CheckRate' not in data:
            # Use free plan default
            data['CheckRate'] = 300
        self._check_fields(data, self.TESTS_FIELDS)
        return self._request('put', self.URL_UPDATE_TEST, data=data, **kwargs).json()

    def update_test(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'TestID' not in data:
            raise StatusCakeFieldMissingError("TestID missing")
        # if CheckRate not passed it will be reset to the account plan default (either 30 or 300)
        if 'CheckRate' not in data:
            raise StatusCakeFieldMissingError("CheckRate missing")
        self._check_fields(data, self.TESTS_FIELDS)
        return self._request('put', self.URL_UPDATE_TEST, data=data, **kwargs).json()

    def get_page_speed(self, **kwargs):
        """ https://www.statuscake.com/api/Page%20Speed/List%20Pagespeed%20Test.md
        """
        return self._request('get', self.URL_PAGE_SPEED, **kwargs).json()

    node_locations = property(get_node_locations)
