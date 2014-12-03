import six
import time
import urllib
import requests
from requests.adapters import HTTPAdapter
from .exceptions import StatusCakeError, StatusCakeAuthError, StatusCakeNotLinkedError, StatusCakeFieldMissingError, StatusCakeFieldError, StatusCakeResponseError


def to_comma_list(value):
    if isinstance(value, (list, tuple, set, frozenset)):
        value = ','.join(value)
    return value


class StatusCake(object):
    URL_LOCATIONS = "https://www.statuscake.com/API/Locations/json"
    URL_ALERT = "https://www.statuscake.com/API/Alerts/?TestID=%s"
    URL_ALL_GROUPS = "https://www.statuscake.com/API/ContactGroups/"
    URL_UPDATE_GROUP = "https://www.statuscake.com/API/ContactGroups/Update/"
    URL_ALL_TESTS = "https://www.statuscake.com/API/Tests/"
    URL_DETAILS_TEST = "https://www.statuscake.com/API/Tests/Details/?TestID=%s"
    URL_UPDATE_TEST = "https://www.statuscake.com/API/Tests/Update"
    URL_AUTH_CHECK = "https://www.statuscake.com/API/Auth/"

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

    TESTS_FIELDS = {
        'TestID': (int, None, None),
        'Paused': (int, (0, 1), None),
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
        'TestType': (six.string_types, ("HTTP", "TCP", "PING"), None),
        'ContactGroup': (int, None, None),
        'RealBrowser': (int, (0, 1), None),
        'TriggerRate': (int, range(0, 61), None),
        'TestTags': (six.string_types, None, to_comma_list),
    }

    def __init__(self, api_key, api_user, timeout=10, auth_check=False):
        self._api_key = api_key
        self._api_user = api_user
        self.timeout = 10
        self._auth_check = auth_check

        self.session = requests.Session()
        self.session.mount('https://www.statuscake.com', HTTPAdapter(max_retries=5))

        if auth_check:
            self.auth_check()

    def _request(self, method, url, data=None, auth_headers=True, check_errors=True, **kwargs):
        headers = {}
        if auth_headers:
            headers.update({
                'API': self._api_key,
                'Username': self._api_user,
            })

        if isinstance(data, dict):
            data = urllib.urlencode(data)

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

    def do_auth_check(self, **kwargs):
        self._request('get', self.URL_AUTH_CHECK, **kwargs).json()
        return True

    def get_user_details(self, **kwargs):
        return self._request('get', self.URL_AUTH_CHECK, **kwargs).json().get('Details', {})

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

    def get_alert(self, test_id, **kwargs):
        return self._request('get', self.URL_ALERT % test_id, **kwargs).json()

    def get_all_tests(self, **kwargs):
        return self._request('get', self.URL_ALL_TESTS, **kwargs).json()

    def get_details_test(self, test_id, **kwargs):
        return self._request('get', self.URL_DETAILS_TEST % test_id, **kwargs).json()

    def delete_test(self, test_id, **kwargs):
        return self._request('delete', self.URL_DETAILS_TEST % test_id, **kwargs).json()

    def insert_test(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'WebsiteName' not in data:
            raise StatusCakeFieldMissingError("WebsiteName missing")
        if 'WebsiteURL' not in data:
            raise StatusCakeFieldMissingError("WebsiteURL missing")
        if 'TestType' not in data:
            raise StatusCakeFieldMissingError("TestType missing")
        self._check_fields(data, self.TESTS_FIELDS)
        return self._request('put', self.URL_UPDATE_TEST, data=data, **kwargs).json()

    def update_test(self, data, **kwargs):
        if not isinstance(data, dict):
            raise StatusCakeError("data argument must be a dict")
        if 'TestID' not in data:
            raise StatusCakeFieldMissingError("TestID missing")
        self._check_fields(data, self.TESTS_FIELDS)
        return self._request('put', self.URL_UPDATE_TEST, data=data, **kwargs).json()

    auth_check = property(do_auth_check)
    user_details = property(get_user_details)
    node_locations = property(get_node_locations)
