import time
import numpy as np
import glob, cv2
import utils
import timeit
import firebase_admin
import requests
from firebase_admin import credentials, storage
from rembg import remove
from datetime import datetime


class volumetric:

    def __init__(self, image_address: str, npz_file: str):

        self.image_address = image_address
        self.origin_image = cv2.imread(image_address) # 튜플 형식으로 받아옴
        self.npz_file = npz_file

        self.h = self.origin_image.shape[0] # 높이 받아오기
        self.w = self.origin_image.shape[1] # 너비 받아오기

    def set_init(self):
        npz = self.npz_file.split("/")[-1]
        npz = npz.split("_")  # cs_(8, 5)_rd_3_te_0.06_rs_4.npz 파일 형식 자르기
        self.checker_sizes = (int(npz[1][1]), int(npz[1][4]))  # 8, 5
        self.check_real_dist = int(npz[3])
        self.resize = int(npz[-1].split(".")[0]) # 4
        # self.resize = int(npz[7][0])

        self.img = cv2.resize(self.origin_image, (self.w // self.resize, self.h // self.resize))
        self.h = self.img.shape[0]
        self.w = self.img.shape[1]

        if "download_img" in self.image_address: # 이게 사람이 지정해주는 폴더명으로 가야함
            self.object_type = "hexahedron"
        else:
            self.object_type = "Error"

    def set_image(self, image_address: str):
        self.img = cv2.imread(image_address)

    # 배경 제거
    def remove_background(self):
        self.remove_bg_image = remove(self.img)

    # 코너 사이즈, 보정 코너들, 회전 벡터, 변환 벡터
    def set_npz_values(self):
        self.camera_matrix, self.dist, self.rvecs, self.tvecs, self.outer_points1, self.checker_sizes = utils.read_npz(
            self.npz_file)

    def find_vertex(self, draw=False):
        '''
        물체 꼭지점 6좌표 추출하는 함수
        draw : 그리기
        '''
        gray_img = cv2.cvtColor(self.remove_bg_image, cv2.COLOR_BGR2GRAY)

        kernel_custom = np.array([[0, 0, 1, 0, 0],
                                  [0, 1, 1, 1, 0],
                                  [1, 1, 1, 1, 1],
                                  [0, 1, 1, 1, 0],
                                  [0, 0, 1, 0, 0]], dtype=np.uint8)
        opening_img = cv2.morphologyEx(gray_img, cv2.MORPH_OPEN, kernel_custom)

        kernel = np.ones((5, 5), np.uint8)
        opening_img = cv2.erode(opening_img, kernel, iterations=1)

        kernel_clear = np.array([[0, -1, 0],
                                 [-1, 9, -1],
                                 [0, -1, 0]])
        # 선명한 커널 적용
        self.object_detection_image = cv2.filter2D(opening_img, -1, kernel_clear)

        # Find contours
        contours, _ = cv2.findContours(self.object_detection_image, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)  # contours는 튜플로 묶인 3차원 array로 출력

        image = self.img.copy()

        # vertex 출력값 그려보기
        vertex_list = list()
        check = 0
        for cnt in contours:
            for eps in np.arange(0.001, 0.2, 0.001):
                length = cv2.arcLength(cnt, True)
                epsilon = eps * length
                vertex = cv2.approxPolyDP(cnt, epsilon, True)

                if self.object_type == "hexahedron" and len(vertex) == 6 and length > (
                        1000 // (self.resize ** 2)):  # vertex가 6 -> 꼭짓점의 갯수
                    vertex_list.append(vertex)
                    self.object_vertexes = np.reshape(vertex_list, (-1, 2))
                    check = 1
                    break
                # hexahedron으로 탐지 하지 못하고 출력을 다르게 하는 경우
                elif self.object_type == "Error" and len(vertex) == 8 and length > (1000 // (self.resize ** 2)):
                    self.vertexes = np.reshape(vertex_list, (-1, 8, 2))
                    quit()
            if check == 1:
                break

        self.vertexes_image = self.img.copy()
        cv2.drawContours(self.vertexes_image, [vertex], 0, (0, 0, 255), 2, cv2.LINE_AA)

        if draw:
            vertexes_image = self.img.copy()
            cv2.drawContours(vertexes_image, [vertex], 0, (0, 0, 255), 1)
            vertexes_image = cv2.resize(vertexes_image, (self.w // 6 * self.resize, self.h // 6 * self.resize))
            cv2.imshow(f"vertexes_image", vertexes_image)
            cv2.waitKey()
            cv2.destroyAllWindows()

        if len(self.object_vertexes) == 0:
            print("object vertexes are not detected....")
            quit()

    def fix_vertex(self):
        '''
        꼭지점 좌표들을 원하는 순서대로 정렬해주는 함수
        '''
        if self.object_type == "hexahedron":
            # 최소 y좌표
            y_coors = np.min(self.object_vertexes, axis=0)[1]

            # 좌상단 좌표가 index 0 번 -> 반시계 방향으로 좌표가 돌아간다.
            contours = self.object_vertexes.tolist()
            while y_coors != contours[-1][1]:
                temp = contours.pop(0)
                contours.append(temp)
            self.object_vertexes = np.array(contours)

    def trans_checker_stand_coor(self):  # point: list, stand_corr: tuple, checker_size: tuple) -> list:
        """
        이미지상의 4개의 좌표를 일정한 간격으로 펴서 4개의 좌표로 만들어주는 함수
        """
        # x, y 비율과 똑같이 ar 이미지에 투시한다.
        # 첫번째 좌표를 기준으로 오른쪽에서 x, 아래쪽 좌표에서 y 간격(비율)을 구해준다.
        # 1칸당 거리 구하기
        one_step = abs(self.outer_points1[0][0] - self.outer_points1[2][0]) / (self.checker_sizes[0] - 1)

        # y_ucl = abs(point[0][1] - point[1][1])

        w, h = (self.w , self.h * 2) # 왜 얘는 2배 안함?
        self.outer_points2 = np.float32(
            [[w, h],
             [w, h + one_step * (self.checker_sizes[1] - 1)],
             [w + one_step * ((self.checker_sizes[0] - 1)), h],
             [w + one_step * ((self.checker_sizes[0] - 1)), h + one_step * (self.checker_sizes[1] - 1)], ]
        )

    # 투시 행렬 구하기
    def set_transform_matrix(self):
        self.transform_matrix = cv2.getPerspectiveTransform(self.outer_points1, self.outer_points2)

    def measure_width_vertical(self):
        """
       printer : 가로, 세로 길이 출력문 실행 여부 - bool
        """
        re_point = list()
        checker_points = self.outer_points1
        checker_points = checker_points.tolist()
        # 체커보드가 정방향으로 투시되었을때 각 좌표들을 다시 구해준다.
        for point in checker_points:
            re_point.append(utils.transform_coordinate(self.transform_matrix, point))

        re_object_points = list()
        re_checker_points = self.object_vertexes.tolist()

        for point in re_checker_points:
            re_object_points.append(utils.transform_coordinate(self.transform_matrix, point))

        # pt2[0]의 x축과 pt2[2]의 x축의 픽셀 거리 // 코너 사이즈 - 1 (칸) = 1칸당 떨어진 픽셀거리
        one_checker_per_pix_dis = abs(re_point[0][0] - re_point[2][0]) / (
                self.checker_sizes[0] - 1
        )

        # 픽셀당 실제 거리 - check_real_dist(cm) / 1칸당 떨어진 픽셀 거리
        self.pix_per_real_dist = self.check_real_dist / one_checker_per_pix_dis # * 1.5

        if self.object_type == "hexahedron":
            # 두 점 사이의 픽셀거리 * 1픽셀당 실제 거리 = 두 점의 실제 거리
            self.width = (
                    utils.euclidean_distance(re_object_points[1], re_object_points[2]) * self.pix_per_real_dist
            )
            self.vertical = (
                    utils.euclidean_distance(re_object_points[2], re_object_points[3]) * self.pix_per_real_dist
            )


    def measure_height(self, draw=True):
        """
        높이 측정 함수
        """
        pts1 = self.outer_points1.tolist()
        ar_start = utils.transform_coordinate(self.transform_matrix, pts1[0])
        ar_second = utils.transform_coordinate(self.transform_matrix, pts1[2])

        vertexes_list = self.object_vertexes[1].tolist()
        ar_object_standard_z = utils.transform_coordinate(self.transform_matrix, vertexes_list)

        # 두 점을 1으로 나눈 거리를 1칸 기준 (ckecker 사이즈에서 1 빼면 칸수)
        ### 이 부분을 자세하게 봐봅시다!! ###
        standard_ar_dist = abs(ar_start[0] - ar_second[0]) / (self.checker_sizes[0] - 1)

        # 실제 세계의 기준 좌표를 기준으로 물체의 z축을 구할 바닥 좌표의 실제 세계의 좌표를 구한다
        # x, y, z 값을 갖는다
        ar_object_real_coor = [
            (ar_object_standard_z[0] - ar_start[0]) / standard_ar_dist,
            (ar_object_standard_z[1] - ar_start[1]) / standard_ar_dist,
            0,
        ]

        # pixel_coordinates
        height_pixel = utils.pixel_coordinates(self.camera_matrix, self.rvecs, self.tvecs, ar_object_real_coor)
        # y축으로 비교해서 z 수치가 증가하다가 물체 높이보다 높아지면 break
        for i in np.arange(0, 10, 0.01):
            if (height_pixel[1] - self.object_vertexes[0][1]) < 0:
                break

            height_pixel = utils.pixel_coordinates(
                self.camera_matrix, self.rvecs, self.tvecs, (ar_object_real_coor[0], ar_object_real_coor[1], -i)
            )
            self.height = i
            if draw:
                self.img = cv2.circle(self.img, tuple(list(map(int, height_pixel[:2]))), 1, (0, 0, 255), -1,
                                      cv2.LINE_AA)

    def draw_image(self, printer=False):
        font = cv2.FONT_HERSHEY_SIMPLEX
        # fontv = cv2.FONT_HERYSHEY_DUPLEX
        # 가로, 세로, 높이 출력
        if self.object_type == "hexahedron":
            printer = True
            if printer:
                print("육면체")
                print("가로길이 :", self.width)
                print("세로길이 :", self.vertical)
                print("높이길이 :", self.height * self.check_real_dist)
                # 부피를 이미지 상에 띄워주자
                print(f"{self.width: .2f} x {self.vertical: .2f} x {(self.height * self.check_real_dist): .2f}")
                # print("부피 :", self.width * self.vertical * self.height * self.check_real_dist)

            # 가로세로높이 그리기
            # 가로
            cv2.putText(self.img, f"{self.width: .2f}cm", (
                self.object_vertexes[1][0] - (self.object_vertexes[1][0] // 3),
                self.object_vertexes[1][1] + ((self.h - self.object_vertexes[1][1]) // 3)), font, (3 / self.resize),
                        (0, 255, 0), (10 // self.resize))
            # 세로
            cv2.putText(self.img, f"{self.vertical: .2f}cm", (
                self.object_vertexes[3][0], self.object_vertexes[1][1] + ((self.h - self.object_vertexes[3][1]) // 3)),
                        font, (3 / self.resize), (255, 0, 0), (10 // self.resize))
            #높이
            cv2.putText(self.img, f"{(self.height * self.check_real_dist): .2f}cm", (
                self.object_vertexes[0][0] - (self.object_vertexes[0][0] // 2),
                (self.object_vertexes[0][1] + self.object_vertexes[1][1]) // 2), font, (3 / self.resize), (0, 0, 255),
                        (10 // self.resize))
            cv2.line(self.img, (self.object_vertexes[1]), (self.object_vertexes[2]), (0, 255, 0), (10 // self.resize),
                     cv2.LINE_AA)
            cv2.line(self.img, (self.object_vertexes[2]), (self.object_vertexes[3]), (255, 0, 0), (10 // self.resize),
                     cv2.LINE_AA)


            # 부피 나타내는 박스 그려봅시다
            # cv2.rectangle(img, pt1, pt2,(0,0,255),3)
            cv2.rectangle(self.img, (550, 10), (750, 80), (0, 255, 0), 3)
            cv2.putText(self.img, "{:.2f}".format(self.width * self.vertical * self.height * self.check_real_dist),
                        (560, 55),
                        font, 1.4, (0, 0, 255), 2)

    def show_image(self, image: np.array, image_name: str):
        window_size_x, window_size_y = 600, 800
        cv2.namedWindow(f"{image_name}", cv2.WINDOW_NORMAL)

        # Using resizeWindow()
        cv2.resizeWindow(f"{image_name}", window_size_x, window_size_y)
        cv2.moveWindow(f"{image_name}", 400, 0)

        # Displaying the image
        cv2.imshow(f"{image_name}", image)
        # cv2.waitKey(0)

        # cv2.destroyAllWindows()

    # save_image를 통해 일단 로컬에 저장할 예정
    def save_image(self, image_address: str, image: np.array):
        cv2.imwrite(image_address, image)

    def time_check(self, time_check_number=10):
        t1 = timeit.timeit(stmt=self.remove_background, number=time_check_number, setup="pass")
        t2_1 = timeit.timeit(stmt=self.find_vertex, number=time_check_number, setup="pass")
        t2_2 = timeit.timeit(stmt=self.fix_vertex, number=time_check_number, setup="pass")
        t3 = timeit.timeit(stmt=self.measure_width_vertical, number=time_check_number, setup="pass")
        t4 = timeit.timeit(stmt=self.measure_height, number=time_check_number, setup="pass")

        # test상에서 time_check함, 불필요한 출력은 줄임
        # print(f"1.remove_background : {t1 / time_check_number} ")
        # print(f"2.find_vertex : {(t2_1 + t2_2) / time_check_number}")
        # print(f"3.measure_width_vertical : {t3 / time_check_number}")
        # print(f"4.measure_height : {t4 / time_check_number}")
        # print(f"total time : {(t1 + t2_1 + t2_2 + t3 + t4) / time_check_number}")


if __name__ == '__main__':
    # 7. 전체
    def main(fname, npz, img_name):
        a = volumetric(fname, npz)
        a.set_init()
        a.set_npz_values()

        # 1. 배경제거
        a.remove_background()

        # 2. 물체 꼭지점 찾기
        a.find_vertex(draw=False)
        a.fix_vertex()

        a.trans_checker_stand_coor()
        a.set_transform_matrix()

        # 3. 가로세로 구하기
        a.measure_width_vertical()

        # 4. 높이 구하기
        a.measure_height(draw=True)

        a.draw_image()

        # a.show_image(a.origin_image, "Origin Image")
        # cv2.waitKey()

        # a.show_image(a.remove_bg_image, "Remove Background")
        # cv2.waitKey(1500)

        # a.show_image(a.object_detection_image, "Object Detection Image")
        # cv2.waitKey(1500)

        # a.show_image(a.vertexes_image, "vertexes Image")
        # cv2.waitKey(1500)

        a.show_image(a.img, "Result Image")
        cv2.waitKey()

        cv2.destroyAllWindows()

        a.save_image(image_address="./upload_img/" + img_name, image=a.img)
        # a.time_check()

        # # 완성된 이미지 위에 부피를 띄울까?
        # ###
        # path = r'C:\Users\Rajnish\Desktop\geeksforgeeks\geeks.png'

        # # Reading an image in default mode
        # image = cv2.imread(path)

        # # Window name in which image is displayed
        # window_name = 'Image'

        # # font
        # font = cv2.FONT_HERSHEY_SIMPLEX

        # # org
        # org = (50, 50)

        # # fontScale
        # fontScale = 1

        # # Blue color in BGR
        # color = (255, 0, 0)

        # # Line thickness of 2 px
        # thickness = 2

        # # Using cv2.putText() method
        # image = cv2.putText(image, 'OpenCV', org, font,
        #                 fontScale, color, thickness, cv2.LINE_AA)
        # # Displaying the image
        # cv2.imshow(window_name, image)
        # ###

        # 이미지 업로드 예시
        local_image_path = "./upload_img/" + img_name  # 자기 컴퓨터 내 이미지 경로
        destination_image_path = "image_result/" + img_name  # Firebase Storage에 저장될 경로, 폴더일 경우 /를 통해 구분
        upload_image(local_image_path, destination_image_path)
        print("upload complete!!!")


    # 자동으로 받아올 수 있는 환경을 구성해보자!!!
    # Firebase Admin SDK 초기화 (한 번만 호출해야 합니다!)
    try:
        # 이미 기존에 초기화된 Firebase 앱이 있는지 확인
        app = firebase_admin.get_app()
    except ValueError as e:
        # 기존에 초기화된 Firebase 앱이 없는 경우에만 초기화
        cred = credentials.Certificate("serviceKey.json")
        # 서비스 계정 - python 비공개 서버키 다운(json)
        # json 파일의 경우 임의로 이름을 바꿨습니다.
        app = firebase_admin.initialize_app(cred, {"storageBucket": "cj-2023-pororo.appspot.com"})
        # storage 주소에서 gs://뺴고 붙여넣기


    def upload_image(local_file_path, destination_file_path):
        # 이미지 업로드
        bucket = storage.bucket(app=app)
        blob = bucket.blob(destination_file_path)
        blob.upload_from_filename(local_file_path)


    # 기존의 다운로드 코드를 이용해보자
    def download_image(destination_file_path, local_file_path):
        # 이미지 다운로드
        bucket = storage.bucket(app=app)
        blob = bucket.blob(destination_file_path)
        blob.download_to_filename(local_file_path)


    # 최신 이미지 URL 가져오기
    def get_latest_image_url():
        bucket = storage.bucket()
        blobs = bucket.list_blobs(prefix="stopbox/")  # 이미지가 저장된 디렉토리명 설정
        # print("1) blobs: ")
        # print(blobs) # blob 아님
        # 1) blobs:
        # <google.api_core.page_iterator.HTTPIterator object at 0x000002202F979C60>
        sorted_blobs = sorted(blobs, key=lambda blob: blob.time_created, reverse=True)
        latest_image_blob = sorted_blobs[0]
        print("test: ")
        # print(latest_image_blob)  # 여기서 2번째 애를 가져와야 하는데
        # print(sorted_blobs[1]) # 얘도 아닌듯
        # test:
        # <Blob: cj-2023-pororo.appspot.com, input/, 1690706608571788>
        # print("2) latest_image_blob: ") # 여기서 파일명도 가져오거든
        # print(latest_image_blob)  # 여기서 2번째 애를 가져와야 하는데
        blob_string = str(latest_image_blob)
        items = blob_string.strip("<>").split(", ")
        # 2번째 항목 추출
        second_item = items[1]
        print(second_item)  # input/202308011335.jpg
        # 파일 이름만 뽑아내자
        tmp = second_item.split("/")
        img_name = tmp[1]
        print(img_name)  # 202308011353.jpeg
        # destination_file_path =
        # print(type(latest_image_blob))
        # 2) latest_image_blob:
        # <Blob: cj-2023-pororo.appspot.com, input/202307311606.jpg, 1690787255953491>

        # 이미지 다운로드
        # download_image(second_item, "./hexahedron/" + img_name)  # 이미지를 다운로드하고 싶은 경로로 수정, 앞이 받는 이미지, 뒤가 파일 받는 경로
        download_image(second_item, "./download_img/" + img_name)  # 이미지를 다운로드하고 싶은 경로로 수정, 앞이 받는 이미지, 뒤가 파일 받는 경로
        time.sleep(3)
        image_path = "./download_img/" + img_name
        npz_name = "cs_(8, 5)_rd_3_te_0.04_rs_4.npz"
        npz_path = "calibration/" + npz_name
        main(image_path, npz_path, img_name)
        # 이미지 업로드


    # 함수 실행
    get_latest_image_url()
