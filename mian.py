import copy
import json
import multiprocessing
from multiprocessing.pool import Pool
from multiprocessing.sharedctypes import Value
import os
import re
import requests
import shutil
import zipfile


def make_backup(file_list: list[str]):
    """
    用于在操作前备份所有可能需要操作的文件
    :return:
    """

    counter: int = 0

    # 创建backup文件夹
    if "backup" not in os.listdir():
        print('makedir "backup"')
        os.makedirs(name="backup")

    backup_file_list = os.listdir(path='backup/')
    # 如果没有对应文件，则备份文件到backup下
    for file in file_list:
        if file not in backup_file_list:
            if counter <= 0:
                print('backup now')
            counter += 1
            shutil.copyfile(src=f"./{file}", dst=f"./backup/{file}")
            print(f'backup "{file}" succeed')


def libre_translator(q):
    url = 'http://127.0.0.1:5000/translate'
    data = {
        'q': q,
        'source': 'en',
        'target': 'zh',
        'format': 'text',
        'alternatives': 3,
        'api_key': ''
    }
    headers = {"Content-Type": "application/json"}
    res = requests.post(url, json=data, headers=headers)
    return res.json()['translatedText']  # 打印翻译后的结果


def jar_translate(__jar_list: list):
    global re_key_of_find_jar
    global re_key_of_find_lang_json
    global re_key_of_find_lang_zh_cn_json
    global re_key_of_find_lang_en_us_json
    global count_jar_min
    global count_jar_max
    if type(__jar_list) is type(str()):
        __jar_list = [f'{__jar_list}']
    for temp_jar_name in __jar_list:
        # print(f'----------{count_jar_min.value}/{count_jar_max.value}----------')
        # print(f'try to open "{temp_jar_name}" with model "read"')
        with zipfile.ZipFile(file=temp_jar_name) as jar:
            name_list_in_jar: list[str] = jar.namelist()
            jar_encoding = 'GBK'
        lang_json_list: list[str] = [x for x in name_list_in_jar if
                                     re_key_of_find_lang_json.match(string=x)]
        # print(f"find *lang/*.json : {lang_json_list}")
        lang_en_us_json_list: list[str] = [x for x in lang_json_list if
                                           re_key_of_find_lang_en_us_json.match(string=x)]
        for en_us_json_file in lang_en_us_json_list:
            if en_us_json_file[:-10] + "zh_cn.json" not in lang_json_list:
                # print(f'not find zh_cn.json in "{en_us_json_file[:-10]}"')
                # print(f"try to open '{temp_jar_name}'")
                with zipfile.ZipFile(file=temp_jar_name) as jar:
                    jar.extract(member=en_us_json_file, path='temp/')
                try:
                    with open(file='./temp/' + en_us_json_file,
                              encoding=jar_encoding) as en_us_json_file_object:
                        en_us: dict[str, str] = json.load(fp=en_us_json_file_object)
                except OSError:
                    jar_encoding = 'UTF-8'
                    with open(file='./temp/' + en_us_json_file,
                              encoding=jar_encoding) as en_us_json_file_object:
                        en_us: dict[str, str] = json.load(fp=en_us_json_file_object)
                zh_cn = copy.deepcopy(en_us)
                zh_cn_value_list = list(zh_cn.values())
                translate_temp_list = libre_translator(q=zh_cn_value_list)
                for key, translate_temp in zip(zh_cn.keys(), translate_temp_list):
                    if zh_cn[key] != translate_temp:
                        zh_cn[key] = translate_temp + '\n(' + zh_cn[key] + ')'
                with open(file='./temp/' + en_us_json_file[:-10] + 'zh_cn.json',
                          mode='w',
                          encoding=jar_encoding) as zh_cn_json_file_object:
                    json.dump(obj=zh_cn, fp=zh_cn_json_file_object, indent=2)
                with zipfile.ZipFile(file=temp_jar_name, mode='a') as jar:
                    jar.write(filename='./temp/' + en_us_json_file[:-10] + 'zh_cn.json',
                              arcname=en_us_json_file[:-10] + 'zh_cn.json')
            with count_jar_min.get_lock():
                # noinspection PyUnresolvedReferences
                count_jar_min.value += 1
                # noinspection PyUnresolvedReferences
                print(
                    f'"{temp_jar_name}" translate successful in {count_jar_min.value}/'
                    f'{count_jar_max}')


def count_jar():
    pass


re_key_of_find_jar = re.compile(pattern=r".*.jar")
re_key_of_find_lang_json = re.compile(pattern=r".*lang/.*.json")
re_key_of_find_lang_en_us_json = re.compile(pattern=r".*lang/en_us.json")
re_key_of_find_lang_zh_cn_json = re.compile(pattern=r".*lang/zh_cn.json")

jar_list: list[str] = [x for x in os.listdir() if
                       re_key_of_find_jar.match(string=x)]  # 获取文件夹中的所有jar文件名称列表

count_jar_max = len(jar_list)
count_jar_min = Value('i', 0)

if __name__ == '__main__':

    if "temp" not in os.listdir():
        print('makedir "temp"')
        os.makedirs(name="temp")

    print(f'find "*.jar" : {jar_list}')

    make_backup(file_list=jar_list)

    with Pool() as p:
        # noinspection PyTypeChecker
        p.map(jar_translate, jar_list)
