import os
import numpy as np
from pypylon import pylon
import cv2
import time

def add_timestamp(image):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    timestamp_ns = str(time.time_ns())[-9:]
    timestamp += '.' + timestamp_ns
    cv2.putText(image, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    return image, timestamp

def initialize_cameras():
    tlFactory = pylon.TlFactory.GetInstance()
    devices = tlFactory.EnumerateDevices()
    print(len(devices))

    if len(devices) < 2:
        print("En az iki kamera bulunmalıdır.")
        return None, None
    
    camera1 = pylon.InstantCamera()
    camera1.Attach(tlFactory.CreateDevice(devices[0]))
    camera1.Open()

    camera2 = pylon.InstantCamera()
    camera2.Attach(tlFactory.CreateDevice(devices[1]))
    camera2.Open()

    camera1.UserSetSelector.SetValue('UserSet3')
    camera1.UserSetLoad.Execute()
    camera2.UserSetSelector.SetValue('UserSet3')
    camera2.UserSetLoad.Execute()

    return camera1, camera2

def create_output_folders():
    output_folder1 = 'camera1_frames'
    output_folder2 = 'camera2_frames'
    output_folder_merged = 'merged_images'
    output_folder_combined_cam1 = 'cam1_combined'
    output_folder_combined_cam2 = 'cam2_combined'
    
    for folder in [output_folder1, output_folder2, output_folder_merged, output_folder_combined_cam1, output_folder_combined_cam2]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            
    return output_folder1, output_folder2, output_folder_merged, output_folder_combined_cam1, output_folder_combined_cam2

def release_cameras(camera1, camera2):
    camera1.StopGrabbing()
    camera2.StopGrabbing()
    camera1.Close()
    camera2.Close()

def main():
    try:
        camera1, camera2 = initialize_cameras()
        if camera1 is None or camera2 is None:
            return
        
        output_folder1, output_folder2, output_folder_merged, output_folder_combined_cam1, output_folder_combined_cam2 = create_output_folders()

        camera1.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        camera2.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        frames_cam1 = []
        frames_cam2 = []
        time_diff_list = []  
        counter = 0

        while True:
            grabResult1 = camera1.RetrieveResult(25000, pylon.TimeoutHandling_ThrowException)
            grabResult2 = camera2.RetrieveResult(25000, pylon.TimeoutHandling_ThrowException)

            if grabResult1.GrabSucceeded() and grabResult2.GrabSucceeded():
                image1 = grabResult1.Array
                image2 = grabResult2.Array

                image1_with_timestamp, timestamp1 = add_timestamp(image1)
                image2_with_timestamp, timestamp2 = add_timestamp(image2)

                width = max(image1_with_timestamp.shape[1], image2_with_timestamp.shape[1])
                
                resized_img1 = cv2.resize(image1_with_timestamp, (width, int(image1_with_timestamp.shape[0] * width / image1_with_timestamp.shape[1])))
                resized_img2 = cv2.resize(image2_with_timestamp, (width, int(image2_with_timestamp.shape[0] * width / image2_with_timestamp.shape[1])))
                
                merged_image = cv2.vconcat([resized_img1, resized_img2])
                
                cv2.imshow('Merged Cameras', merged_image)
                
                time_diff = abs(int(timestamp1[-9:]) - int(timestamp2[-9:]))
                time_diff_ms = time_diff / 10**6 
                time_diff_ms_formatted = "{:.3f}".format(time_diff_ms)  
                print(f"Image {counter}: Time difference between camera1 and camera2: {time_diff_ms_formatted} ms")
                
                time_diff_list.append(time_diff_ms)  

                cv2.imwrite(os.path.join(output_folder1, f"camera1_{timestamp1}.png"), image1_with_timestamp)
                cv2.imwrite(os.path.join(output_folder2, f"camera2_{timestamp2}.png"), image2_with_timestamp)
                
                frames_cam1.append(image1_with_timestamp)
                frames_cam2.append(image2_with_timestamp)
                
                combined_image_cam1 = cv2.vconcat(frames_cam1)
                combined_image_cam2 = cv2.vconcat(frames_cam2)
                
                max_height = max(combined_image_cam1.shape[0], combined_image_cam2.shape[0])
                combined_image_cam1_resized = cv2.resize(combined_image_cam1, (combined_image_cam1.shape[1], max_height))
                combined_image_cam2_resized = cv2.resize(combined_image_cam2, (combined_image_cam2.shape[1], max_height))
                
                file_name_combined_cam1 = os.path.join(output_folder_combined_cam1, f"combined_cam1.png")
                file_name_combined_cam2 = os.path.join(output_folder_combined_cam2, f"combined_cam2.png")
                
                cv2.imwrite(file_name_combined_cam1, combined_image_cam1_resized)
                cv2.imwrite(file_name_combined_cam2, combined_image_cam2_resized)
                
                gap = np.zeros((max_height, 1500), dtype=np.uint8)

                combined_horizontal = np.hstack((combined_image_cam1_resized, gap, combined_image_cam2_resized))

                cv2.imwrite(os.path.join(output_folder_merged, f"combined_horizontal.png"), combined_horizontal)

                counter += 1  

            grabResult1.Release()
            grabResult2.Release()

            key = cv2.waitKey(1)  
            if key & 0xFF == ord('q'):
                break  

        release_cameras(camera1, camera2)
        cv2.destroyAllWindows()
        
    except Exception as e:
        print("An error occurred:", e)

        avg_time_diff_ms = sum(time_diff_list) / len(time_diff_list)
        print("Average:", avg_time_diff_ms)

        print("Total number of images captured:", counter)  


if __name__ == "__main__":
    main()
