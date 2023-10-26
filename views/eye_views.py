from flask import Blueprint, request, jsonify
import os
import cv2
from skimage.feature import hog
import pickle
import pymysql

#path adjusting
def get_path(path):
    change_path = path.replace("\\",'/')
    return change_path

bp = Blueprint('eye', __name__, url_prefix='/eye')

# eye.pkl의 상대 경로 계산
path = '../eye/SVM-Classifier/eye_model.pkl'
classify_path = get_path(os.path.abspath(path))

# SVM 모델 로드
with open(classify_path, 'rb') as model_file:
    svm_model = pickle.load(model_file)

categories = ['cataracts', 'cherry_eye', 'normal']

# db
def db_connector():
    db_params = {
        'host': 'localhost',
        'user': 'root',
        'password': 'Qwer12345678!',
        'db': 'pet_connect',
        'charset': 'utf8',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    connector = pymysql.connect(**db_params)
    return connector

@bp.route('/', methods=['POST'])
def analyze_eye():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part', 'message': 'fail'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file', 'message': 'fail'})

    if file:
        # Create the 'uploads' directory if it doesn't exist
        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        # Save the uploaded image to a temporary location
        image_path = os.path.join('uploads', file.filename)
        file.save(image_path)

        # Load and preprocess the image
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        preprocessed_image = cv2.resize(image, (64, 64))
        hog_features = hog(preprocessed_image, orientations=8, pixels_per_cell=(16, 16), cells_per_block=(1, 1))

        # Predict the eye category using SVM model
        predicted_label = svm_model.predict([hog_features])[0]
        predicted_category = categories[predicted_label]

        # Remove the temporary image file
        os.remove(image_path)

        # Store the result in the database
        try:
            db_conn = db_connector()
            cursor = db_conn.cursor()

            query = "INSERT INTO eye_results (dogRegistNum, predicted_category) VALUES (%s, %s)"
            values = (request.form['dogRegistNum'], predicted_category)
            cursor.execute(query, values)
            db_conn.commit()

            cursor.close()
            db_conn.close()

            return jsonify({'result': predicted_category, 'message': 'success'})

        except Exception as e:
            print("Error storing result in the database:", e)
            return jsonify({'error': 'Failed to store result in the database', 'message': 'faill'})

@bp.route('/<dogRegistNum>', methods=['GET'])
def get_eye_result(dogRegistNum):
    try:
        db_conn = db_connector()
        cursor = db_conn.cursor()

        query = "SELECT predicted_category FROM eye_results WHERE dogRegistNum = %s"
        values = (dogRegistNum,)
        cursor.execute(query, values)
        result = cursor.fetchone()

        cursor.close()
        db_conn.close()

        if result:
            return jsonify({'result': result['predicted_category']})
        else:
            return jsonify({'error': 'No result found'})

    except Exception as e:
        print("Error retrieving result from database:", e)
        return jsonify({'error': 'Failed to retrieve result from database'})