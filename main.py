from flask import Flask, request, jsonify
import shutil
import os
from parseFunctions import *
from SQL_keyword_llama_guard.keyword_guard import *
from SQL_keyword_llama_guard.utils import *
from SQL_keyword_llama_guard.llama_guard import *
from waitress import serve
import logging
import uuid
from enum import Enum
    

app = Flask(__name__)

class StatusCode(Enum):
    SAFE = 0
    UNSAFE = 1
    UNSURE = 2

@app.route('/guard', methods=['POST'])
def guard():
    try:
        # 從請求中取得檔案路徑
        data = request.get_json()
        file_path = data.get('file_path')
        file_name = data.get('file_name')
        # 共享測試機
        file_path = "Z:/" + file_path
        # 判斷是否有附上檔案路徑
        if not file_path or not file_name:
            return jsonify({"error": "File path/name is required"}), 400
        # 判斷是否為指向檔案的路徑
        if not os.path.isfile(file_path):
            return jsonify({"error": f"Invalid file path {file_path}"}), 400

        else:
            # 暫複製一份無副檔名的檔案並賦予其正確的檔名副檔名(自db mapping取得)
            temp_path = os.path.join("./file_working_area", str(uuid.uuid4())+file_name)
            shutil.copy(file_path, temp_path)

            # 取得副檔名
            flag, extract_status, result = extract_text(temp_path)
            # 刪除複製之檔案
            os.remove(temp_path)
            # 判斷檔案parsing是否有成功、且為可解析之檔案格式
            if flag and extract_status is not None:
                message = ""
                if extract_status is True:
                    message = "【本檔案被偵測出含有圖片】"
                # Keyword Guard
                keyword_feedbacks = keyword_moderator.get_feedback(result)
                keyword_status, keyword_result = file_feedback(keyword_feedbacks)

                # Llama Guard
                feedbacks = moderator.get_feedback(result)
                status, result = file_feedback(feedbacks)

                message = message + (keyword_result or '') + (result or '')

                # 輸出結果
                if (status == StatusCode.SAFE.value and keyword_status == StatusCode.SAFE.value and extract_status) or (
                        status == StatusCode.SAFE.value and keyword_status == StatusCode.UNSAFE.value) or (
                        status == StatusCode.UNSAFE.value and keyword_status == StatusCode.SAFE.value):
                    # 若文字過濾通過、但檔案倍偵測含有圖片、超連結，則改為不確定(回傳代碼為2)、或keyword guard、llama guard有其一偵測出危害
                    return_status = StatusCode.UNSURE.value
                elif status == StatusCode.SAFE.value or keyword_status == StatusCode.SAFE.value:
                    return_status = StatusCode.SAFE.value
                else:
                    return_status = StatusCode.UNSAFE.value
                
                return jsonify({"status": return_status, "message": message}), 200
            elif flag and extract_status is None:
                # 無法解析之檔案格式、回傳不確定及訊息
                return_status = StatusCode.UNSURE.value
                return jsonify({"status": return_status, "message": result}), 200
            else:
                # 檔案解析過程發生Exception
                return jsonify({"message": "extract" + result}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@app.after_request
def log_request_info(response):
    client_ip = request.remote_addr
    status_code = response.status_code
    logging.info(f"Client IP: {client_ip}, Status Code: {status_code}")
    return response


if __name__ == '__main__':
    # 啟動llama guard
    keyword_moderator = KeywordGuard(db_config,debug_mode=True)
    moderator = LlamaGuard(debug_mode=True)


    # 設置 logging 記錄日誌到文件
    logging.basicConfig(
        filename='',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info(f"TAIDE Data Safety Guard Starting!")
    serve(app, host='', port='')