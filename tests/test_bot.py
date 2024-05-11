from unittest import TestCase, mock


from my_store.sms_bot import check_response


class BotTestCase(TestCase):

    def test_check_response(self):
        test_response_0 = {"rows": [1, 2, 3], "fake_key_2": "fake_value_2"}
        test_response_1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        test_response_2 = {"fake_key_1": "fake_value_1", "fake_key_2": "fake_value_2"}
        test_response_3 = {"rows": "not_list", "fake_key_2": "fake_value_2"}
        test_response_4 = {"rows": None, "fake_key_2": "fake_value_2"}

        param_list = [
            (test_response_1, TypeError),
            (test_response_2, KeyError),
            (test_response_3, TypeError),
            (test_response_4, KeyError),
        ]
        assert check_response(test_response_0) == [1, 2, 3]
        for test_response, error_expected in param_list:
            with self.subTest(test_response=test_response, error_expected=error_expected):
                self.assertRaises(error_expected, check_response, test_response)



