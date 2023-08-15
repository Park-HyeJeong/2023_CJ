from flask import Flask
#from app.volume_measure import get_latest_image_url
import volume_measure

app = Flask(__name__)

@app.route('/measure', methods=['POST','GET'])
def measure_image():
    volume_measure.get_latest_image_url()
    return 'testing'

if __name__ == '__main__':
    app.run(debug=True)
