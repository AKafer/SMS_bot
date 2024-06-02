from my_store.devino_integration import ClassDevinoAPI
from my_store.mts_integration import ClassMtsAPI

final_user_list = [
    {
        "name": "Photon",
        "phone": "7-916-354-21-92",
        "lastDemandDate": "2021-10-10 17:10:10",
    }
]


# def test_devino(final_user_list):
#     client = ClassDevinoAPI()
#     print('Начинаю рассылку смс')
#     final_user_list, start_balance = client.sms_send(final_user_list)
#     print('Рассылка закончена')
#     print('Формирование отчета по смс')
#     report = client.sms_report(final_user_list, start_balance)
#     print('Отчет сформирован')
#     print(report)
#     print(final_user_list)

def notest_mts(final_user_list):
    client = ClassMtsAPI()
    print('Начинаю рассылку смс')
    final_user_list, start_balance = client.sms_send(final_user_list)
    print('Рассылка закончена')
    print('Формирование отчета по смс')
    report = client.sms_report(final_user_list, start_balance)
    print('Отчет сформирован')
    print(report)
    print(final_user_list)


# test_devino(final_user_list)
notest_mts(final_user_list)
