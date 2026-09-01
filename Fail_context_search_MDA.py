import sys
import json
import Content_analysis_MDA
import traceback
from datetime import datetime
import time
import os
import psutil
import random
import string


def main(path, operID):
    with open(os.getcwd() + "/Info.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    file_content = ''.join(lines[1:])
    data = json.loads(file_content)
    files = os.listdir(path)
    dcl_files = [f for f in files if f.endswith(
        '.dcl') and os.path.isfile(os.path.join(path, f))]
    for filename in dcl_files:
        try:
            current_time = datetime.now()
            start_time = time.time()
            slot, test_result, sn, result = Content_analysis_MDA.Log_analysis(
                path, filename)
            if test_result == "SKIP":
                os.remove(path + filename)
                continue
            status_code, content = Content_analysis_MDA.Upload_to_TIS(
                slot, result, sn, filename, test_result, operID)
            end_time = time.time()
            execution_time = end_time - start_time
            time_str = current_time.strftime("%Y-%m-%d")
            file_path = "D:/TIS/" + data["projectProduct"] + "/"
            os.makedirs(file_path, exist_ok=True)
            file_name = file_path + "TIS_Upload_log_" + \
                time_str + "_" + test_result + ".txt"
            with open(file_name, "a", encoding="utf-8") as file:
                file.write(content)
                if status_code == 200:
                    file.write("\nStatus Code:200")
                    file.write("\nUpload Success!!\n")
                else:
                    file.write("\nStatus Code:" + str(status_code))
                    file.write(
                        "\nUpload Fail!! Please Check Info.txt & Log File is exist!!\n")
                time_str = current_time.strftime("%Y-%m-%d %H:%M:%S\n")
                file.write(time_str)
                file.write(f"Tool execution time : {execution_time:.2f} secs")
                file.write("\n========================================\n")
            os.remove(path + filename)
        except Exception as e:
            # status_code, content = Content_analysis_MDA.Upload_to_TIS(
            #     "", "", "", filename, "")
            error_info = traceback.format_exc()
            time_str = current_time.strftime("%Y-%m-%d")
            file_name = "D:/TIS/" + data["projectProduct"] + \
                "/TIS_Upload_errorlog_" + time_str + ".txt"
            with open(file_name, "a", encoding="utf-8") as file:
                file.write(error_info)
                time_str = current_time.strftime("%Y-%m-%d %H:%M:%S\n")
                file.write(filename + "\n")
                file.write(time_str)
                file.write("========================================\n")
            print(error_info)


def is_application_running(application_name):
    for process in psutil.process_iter(['name']):
        if process.info['name'] and application_name.lower() in process.info['name'].lower():
            return True
    return False


def generate_random_code(length=14):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


if __name__ == "__main__":
    # mode: 1:Upload TIS
    #       2:Upload Fake TIS
    #       3:Request from MARS to Testing
    #       4:Debug -- Update MARS status
    try:
        mode = sys.argv[1].split()[0]
    except Exception as e:
        mode = sys.argv[1]
    if mode == "1":
        app_name = "MATST826.exe"  # 小烏龜
        path = os.getcwd() + "/TIS_Log/"
        operID = "NULL"
        if is_application_running(app_name):
            operID = "Online"
        main(path, operID)
    elif mode == "2":
        args = sys.argv[2]
        param = args.split()
        time_str = datetime.now().strftime("%Y%m%d")
        random_sn = generate_random_code()
        log_name = random_sn + "_" + time_str + ".txt"
        status_code, content = Content_analysis_MDA.Upload_to_TIS_Fake(
            param, random_sn, log_name)
        file_path = "D:/TIS/" + param[3] + "/"
        os.makedirs(file_path, exist_ok=True)
        file_name = file_path + "TIS_Upload_log_" + \
            time_str + "_PASS.txt"
        for filename in os.listdir(file_path):
            if filename.startswith(param[3]):
                path = os.path.join(file_path, filename)
                os.remove(path)
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(content)
            if status_code == 200:
                file.write("\nStatus Code:200")
                file.write("\nUpload Success!!\n")
            else:
                file.write("\nStatus Code:" + str(status_code))
                file.write(
                    "\nUpload Fail!! Please check if the internet is working.\n")
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S\n")
            file.write(time_str)
            file.write("========================================\n")
        file_name = file_path + "FAIL-STOP_" + \
            datetime.now().strftime("%Y-%m-%d") + ".txt"
        with open(file_name, "a", encoding="utf-8") as file_STOP:
            str = param[3] + \
                " : PASS\nSN : FAKE\nAlready upload Fake data by TIS_Tool_MDA_Fake.bat\n"
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S\n")
            Content_analysis_MDA.Log_ouput(file_STOP, str, time_str)
    elif mode == "3":
        app_name = "MATST826.exe"  # 小烏龜
        file_path = "D:/TIS/"
        file_name = file_path + "MARS_reply.txt"
        if is_application_running(app_name):
            machine_number, response_MARS = Content_analysis_MDA.Request_to_MARS()
            if response_MARS == "9":  # STOP
                with open(file_name, "w", encoding="utf-8") as file_STOP:
                    file_STOP.write(machine_number + ":0")
                    Content_analysis_MDA.show_msg(machine_number+"is shutdown")
            else:  # Testing
                with open(file_name, "w", encoding="utf-8") as file_STOP:
                    file_STOP.write(machine_number + ":1")
        else:
            with open(file_name, "w", encoding="utf-8") as file_STOP:
                file_STOP.write(" ")

    elif mode == "4":
        # result = sys.argv[2]
        Info_list = ['slot', 'sub', 'sn', 'filename', 'FAIL', '11209647']
        status_code_TIS, content_TIS = Content_analysis_MDA.Upload_to_TIS(
            'slot', 'sub', 'sn', 'filename', 'FAIL', '11209647')

        file_name = "D:/TIS/MARS_Upload_log.txt"
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(content_TIS)
