# coding=utf-8
import os
import platform
import tkinter
from tkinter import *
from HCNetSDK import *
from PlayCtrl import *
from time import sleep
import time
from PIL import Image
import queue
import numpy as np
from yolo import YOLO, YOLO_ONNX
import math
import threading
# 创建一个线程安全的队列
file_queue = queue.Queue()
# 登录的设备信息
DEV_IP = create_string_buffer(b'169.254.104.194')
DEV_PORT = 8000
DEV_USER_NAME = create_string_buffer(b'admin')
DEV_PASSWORD = create_string_buffer(b'gyb18800')
import cv2
WINDOWS_FLAG = True
win = None  # 预览窗口
funcRealDataCallBack_V30 = None  # 实时预览回调函数，需要定义为全局的
PlayCtrl_Port = c_long(-1)  # 播放句柄
Playctrldll = None  # 播放库
FuncDecCB = None   # 播放库解码回调函数，需要定义为全局的
i1 = 0
yolo = YOLO()
crop            = False
count           = False

mode=1   #mode=1代表跟踪，mode=0代表预测
def calculate_dynamic_sleep(diff_x, diff_y, max_diff, min_sleep, max_sleep):
    # 计算总的距离
    distance = math.sqrt(diff_x ** 2 + diff_y ** 2)

    # 归一化距离并映射到sleep时间
    sleep_time = min(distance/ 400 * 0.1, max_sleep) 
    print(sleep_time)
    return sleep_time


def display_image():
    while True:
        # 从队列中获取最新的文件名
        sFileName = file_queue.get()

        # 加载并显示图像
        frame = cv2.imread(sFileName)
        if frame is not None:
            frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            # 转变成Image
            frame = Image.fromarray(np.uint8(frame))
            # 进行检测
            frame,kuang=yolo.detect_image(frame, crop = crop, count=count)
            frame = np.array(frame)
            # RGBtoBGR满足opencv显示格式
            frame = cv2.cvtColor(frame,cv2.COLOR_RGB2BGR)
            cv2.imshow('Image', frame)

            
            # ... [图像处理和检测代码] ...
            if kuang is not None:
               # 计算框的中心点
                box_center_x = (kuang[0] + kuang[2]) / 2
                box_center_y = (kuang[1] + kuang[3]) / 2

                if mode:
                    # 计算图像的中心点
                    img_center_x = frame.shape[1] / 2
                    img_center_y = frame.shape[0] / 2

                    # 设置移动的阈值
                    threshold = 20  # 可以根据需要调整这个值

                    # 计算框中心与图像中心的差异
                    diff_x = box_center_x - img_center_x
                    diff_y = box_center_y - img_center_y

                    # 根据位置差异选择控制命令
                    command = None
                    if abs(diff_x) > threshold or abs(diff_y) > threshold:
                        dynamic_sleep = calculate_dynamic_sleep(diff_x, diff_y, 200, 0.1, 0.5)  # 参数可根据需要调整
                        if diff_x < -threshold and diff_y < -threshold:
                            command = UP_LEFT
                        elif diff_x > threshold and diff_y < -threshold:
                            command = UP_RIGHT
                        elif diff_x < -threshold and diff_y > threshold:
                            command = DOWN_LEFT
                        elif diff_x > threshold and diff_y > threshold:
                            command = DOWN_RIGHT
                        elif diff_x < -threshold:
                            command = PAN_LEFT
                        elif diff_x > threshold:
                            command = PAN_RIGHT
                        elif diff_y < -threshold:
                            command = TILT_UP
                        elif diff_y > threshold:
                            command = TILT_DOWN
                    # 控制摄像头移动
                    if command is not None:
                        Objdll.NET_DVR_PTZControl(lRealPlayHandle, command, 0)
                        time.sleep(dynamic_sleep)
                        Objdll.NET_DVR_PTZControl(lRealPlayHandle, command, 1)
                        # //TILT_UP            21    /* 云台以SS的速度上仰 */
                        # //TILT_DOWN        22    /* 云台以SS的速度下俯 */
                        # //PAN_LEFT        23    /* 云台以SS的速度左转 */
                        # //PAN_RIGHT        24    /* 云台以SS的速度右转 */
                        # //UP_LEFT            25    /* 云台以SS的速度上仰和左转 */
                        # //UP_RIGHT        26    /* 云台以SS的速度上仰和右转 */
                        # //DOWN_LEFT        27    /* 云台以SS的速度下俯和左转 */
                        # //DOWN_RIGHT        28    /* 云台以SS的速度下俯和右转 */
                        # //PAN_AUTO        29    /* 云台以SS的速度左右自动扫描 */
                else:
                    pass
                    #TODO：运动目标轨迹预测
                    
            key = cv2.waitKey(50) & 0xFF
            if key == ord('q'):
                break
        else:
            print("无法读取图像，请检查文件路径")

    cv2.destroyAllWindows()

def start_image_display_thread():
    display_thread = threading.Thread(target=display_image)
    display_thread.daemon = True
    display_thread.start()

# 获取当前系统环境
def GetPlatform():
    sysstr = platform.system()
    print('' + sysstr)
    if sysstr != "Windows":
        global WINDOWS_FLAG
        WINDOWS_FLAG = False

# 设置SDK初始化依赖库路径
def SetSDKInitCfg():
    # 设置HCNetSDKCom组件库和SSL库加载路径
    # print(os.getcwd())
    if WINDOWS_FLAG:
        strPath = os.getcwd().encode('gbk')
        sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
        sdk_ComPath.sPath = strPath
        Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
        Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'\libcrypto-1_1-x64.dll'))
        Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'\libssl-1_1-x64.dll'))
    else:
        strPath = os.getcwd().encode('utf-8')
        sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
        sdk_ComPath.sPath = strPath
        Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
        Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'/libcrypto.so.1.1'))
        Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'/libssl.so.1.1'))

def LoginDev(Objdll):
    # 登录注册设备
    device_info = NET_DVR_DEVICEINFO_V30()
    lUserId = Objdll.NET_DVR_Login_V30(DEV_IP, DEV_PORT, DEV_USER_NAME, DEV_PASSWORD, byref(device_info))
    return (lUserId, device_info)

def DecCBFun(nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
    # 解码回调函数
    global i1  # 声明 i1 为全局变量
    if pFrameInfo.contents.nType == 3:
        # 解码返回视频YUV数据，将YUV数据转成jpg图片保存到本地
        # 如果有耗时处理，需要将解码数据拷贝到回调函数外面的其他线程里面处理，避免阻塞回调导致解码丢帧
        sFileName = ('../../pic/test_stamp[%d].jpg'% pFrameInfo.contents.nStamp)#
        nWidth = pFrameInfo.contents.nWidth
        nHeight = pFrameInfo.contents.nHeight
        nType = pFrameInfo.contents.nType
        dwFrameNum = pFrameInfo.contents.dwFrameNum
        nStamp = pFrameInfo.contents.nStamp
        print(nWidth, nHeight, nType, dwFrameNum, nStamp, sFileName)

        lRet = Playctrldll.PlayM4_ConvertToJpegFile(pBuf, nSize, nWidth, nHeight, nType, c_char_p(sFileName.encode()))

        if i1==10:
            file_queue.put(sFileName)
            i1=0
        i1=i1+1

        #show_image(sFileName )
        # 示例用法
        # draw_box_and_save(sFileName, (50, 50, 150, 150))  
        # sleep(1)

        if lRet == 0:
            print('PlayM4_ConvertToJpegFile fail, error code is:', Playctrldll.PlayM4_GetLastError(nPort))
        else:
            print('PlayM4_ConvertToJpegFile success')




def RealDataCallBack_V30(lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
    # 码流回调函数
    if dwDataType == NET_DVR_SYSHEAD:
        # 设置流播放模式
        Playctrldll.PlayM4_SetStreamOpenMode(PlayCtrl_Port, 0)
        # 打开码流，送入40字节系统头数据
        if Playctrldll.PlayM4_OpenStream(PlayCtrl_Port, pBuffer, dwBufSize, 1024*1024):
            # 设置解码回调，可以返回解码后YUV视频数据
            global FuncDecCB
            FuncDecCB = DECCBFUNWIN(DecCBFun)
            Playctrldll.PlayM4_SetDecCallBackExMend(PlayCtrl_Port, FuncDecCB, None, 0, None)
            # 开始解码播放
            if Playctrldll.PlayM4_Play(PlayCtrl_Port, cv.winfo_id()):
                print(u'播放库播放成功')
            else:
                print(u'播放库播放失败')
        else:
            print(u'播放库打开流失败')
    elif dwDataType == NET_DVR_STREAMDATA:
        Playctrldll.PlayM4_InputData(PlayCtrl_Port, pBuffer, dwBufSize)
    else:
        print (u'其他数据,长度:', dwBufSize)

def OpenPreview(Objdll, lUserId, callbackFun):
    '''
    打开预览
    '''
    preview_info = NET_DVR_PREVIEWINFO()
    preview_info.hPlayWnd = 0
    preview_info.lChannel = 1  # 通道号
    preview_info.dwStreamType = 0  # 主码流
    preview_info.dwLinkMode = 0  # TCP
    preview_info.bBlocked = 1  # 阻塞取流

    # 开始预览并且设置回调函数回调获取实时流数据
    lRealPlayHandle = Objdll.NET_DVR_RealPlay_V40(lUserId, byref(preview_info), callbackFun, None)
    return lRealPlayHandle

def InputData(fileMp4, Playctrldll):
    while True:
        pFileData = fileMp4.read(4096)
        if pFileData is None:
            break

        if not Playctrldll.PlayM4_InputData(PlayCtrl_Port, pFileData, len(pFileData)):
            break

if __name__ == '__main__':
    # 创建窗口
    win = tkinter.Tk()
    #固定窗口大小
    win.resizable(0, 0)
    win.overrideredirect(True)

    sw = win.winfo_screenwidth()
    # 得到屏幕宽度
    sh = win.winfo_screenheight()
    # 得到屏幕高度

    # 窗口宽高
    ww = 512
    wh = 384
    x = (sw - ww) / 2
    y = (sh - wh) / 2
    win.geometry("%dx%d+%d+%d" % (ww, wh, x, y))

    # 创建退出按键
    b = Button(win, text='退出', command=win.quit)
    b.pack()
    # 创建一个Canvas，设置其背景色为白色
    cv = tkinter.Canvas(win, bg='white', width=ww, height=wh)
    cv.pack()

    # 获取系统平台
    GetPlatform()

    # 加载库,先加载依赖库
    if WINDOWS_FLAG:
        os.chdir(r'./lib/win')
        Objdll = ctypes.CDLL(r'./HCNetSDK.dll')  # 加载网络库
        Playctrldll = ctypes.CDLL(r'./PlayCtrl.dll')  # 加载播放库
    else:
        os.chdir(r'./lib/linux')
        Objdll = cdll.LoadLibrary(r'./libhcnetsdk.so')
        Playctrldll = cdll.LoadLibrary(r'./libPlayCtrl.so')

    SetSDKInitCfg()  # 设置组件库和SSL库加载路径

    # 初始化DLL
    Objdll.NET_DVR_Init()
    # 启用SDK写日志
    Objdll.NET_DVR_SetLogToFile(3, bytes('./SdkLog_Python/', encoding="utf-8"), False)
   
    # 获取一个播放句柄
    if not Playctrldll.PlayM4_GetPort(byref(PlayCtrl_Port)):
        print(u'获取播放库句柄失败')

    # 登录设备
    (lUserId, device_info) = LoginDev(Objdll)
    if lUserId < 0:
        err = Objdll.NET_DVR_GetLastError()
        print('Login device fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
        # 释放资源
        Objdll.NET_DVR_Cleanup()
        exit()

    # 定义码流回调函数
    funcRealDataCallBack_V30 = REALDATACALLBACK(RealDataCallBack_V30)
    # 开启预览
    lRealPlayHandle = OpenPreview(Objdll, lUserId, funcRealDataCallBack_V30)
    if lRealPlayHandle < 0:
        print ('Open preview fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
        # 登出设备
        Objdll.NET_DVR_Logout(lUserId)
        # 释放资源
        Objdll.NET_DVR_Cleanup()
        exit()

    start_image_display_thread()
    #show Windows
    win.mainloop()

    # 关闭预览
    Objdll.NET_DVR_StopRealPlay(lRealPlayHandle)

    # 停止解码，释放播放库资源
    if PlayCtrl_Port.value > -1:
        Playctrldll.PlayM4_Stop(PlayCtrl_Port)
        Playctrldll.PlayM4_CloseStream(PlayCtrl_Port)
        Playctrldll.PlayM4_FreePort(PlayCtrl_Port)
        PlayCtrl_Port = c_long(-1)

    # 登出设备
    Objdll.NET_DVR_Logout(lUserId)

    # 释放资源
    Objdll.NET_DVR_Cleanup()