import numpy as np
import glob, cv2


def find_checker_outer_points(refined_corners: np.array, checker_sizes: tuple, printer=False):
    """
    points: cv2.cornerSubPix()에 의해 생성된 점들
    size: 체스판의 크기
    """
    points = refined_corners # 아래에서 refined_corners
    size = checker_sizes # (i,j)

    outer_points = np.float32(
        [
            points[0][0], # 체스판 좌상단
            points[size[0] * (size[1] - 1)][0], # 체스판 우상단
            points[size[0] - 1][0],
            points[(size[0] * (size[1] - 1)) + (size[0] - 1)][0],
        ]
    )
    if printer:
        print(size[0], size[1])
        print("0th", points[0][0])
        print("1st", points[size[0] * (size[1] - 1)][0])
        print("2nd", points[size[0] - 1][0])
        print("3rd", points[(size[0] * (size[1] - 1)) + (size[0] - 1)][0])

    return outer_points


calibration_path = "./calibration"

if __name__ == "__main__":
    images = glob.glob(calibration_path + "/*.jpg")

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 1000, 0.0001)
    # criteria = (cv2.TERM_CRITERIA_EPS, 30, 0.00001)

    #### 사용자가 입력해야되는 값 ####
    # checker_sizes : i, j
    # real_dist : 실제 체크보드 1칸 길이

    # 체크보드 길이를 측정해서 이를 바탕으로 새롭게 넣어줘야함
    real_dist = 3

    # resize 별 npz 파일 만들기
    for resize in range(7, 1, -1):
        print("resize :", resize)
        i, j = (8, 5)
        imgpoints = []
        objpoints = []
        for fname in images:
            print("imgpoints", len(imgpoints))
            print(fname)  # 파일 이름 출력
            img = cv2.imread(fname).copy()
            h, w = img.shape[:2]
            image = cv2.resize(img, (w // resize, h // resize))
            # print(img.shape[:2])
            # print(image)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            ret, corners = cv2.findChessboardCorners(gray, (i, j), None)
            if ret == True:
                objp = np.zeros((i * j, 3), np.float32)
                objp[:, :2] = np.mgrid[0:i, 0:j].T.reshape(-1, 2)
                objpoints.append(objp)
                # print(checker_sizes)
                checker_sizes = (i, j)

                refined_corners = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1), criteria
                )
                imgpoints.append(refined_corners)
                # # 코너를 그리고 봐보자
                # img = cv2.drawChessboardCorners(img, (8, 5), refined_corners, ret)
                # cv2.namedWindow('img', cv2.WINDOW_NORMAL)
                # cv2.resizeWindow('img', 800, 800)  # 예시 크기
                # cv2.imshow('img', img)
                # cv2.waitKey(2000)
                # Test
                # image = cv2.imread('./calibration/1 (1).jpg', cv2.IMREAD_GRAYSCALE)
                # for corner in refined_corners:
                #     x, y = corner.ravel()
                #     cv2.line(image, (i, j), 3, 255, -1)
                # cv2.namedWindow('Image Window', cv2.WINDOW_NORMAL)
                # cv2.resizeWindow('Image Window', 600, 600)  # 예시 크기
                # cv2.imshow('Image Window',image)
                # print("corner is  detected !!!")

            else:
                print("corner is not detected......")

        if len(imgpoints) != 0:
            ret, camera_matrix, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None,
                                                                         None)

            # calibration error
            tot_error = 0
            for i in range(len(objpoints)):
                imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist)
                error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                tot_error += error
                print(i + 1, error)

            ret, rvecs, tvecs = cv2.solvePnP(objp, refined_corners, camera_matrix, dist)
            outer_points = find_checker_outer_points(refined_corners, checker_sizes)
            total = tot_error / len(objpoints)
            print("total error: ", tot_error / len(objpoints))

            if ret == True:
                np.savez(calibration_path + f"/cs_{checker_sizes}_rd_{real_dist}_te_{total:.2f}_rs_{resize}.npz",
                         ret=ret, mtx=camera_matrix, dist=dist, rvecs=rvecs, tvecs=tvecs, outer_points=outer_points,
                         checker_size=checker_sizes)