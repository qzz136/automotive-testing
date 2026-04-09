#define TSMP_IMPL
#include "TSMasterMP.h"
#include "MPLibrary.h"
#include "Database.h"
#include "Test.h"
//#include <windows.h>
#include <stdlib.h>
#include <stdio.h>
#include <direct.h>
#include <winsock2.h>  
#include <ws2tcpip.h> 
#include <mswsock.h>
#include <time.h>
#include <locale.h>
#include <curl/curl.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/stat.h>
#include <opencv2/opencv.hpp>
#include <openssl/evp.h>
#include <openssl/err.h>
#pragma comment(lib,"libssl.lib")
#pragma comment(lib,"libcrypto.lib")
#pragma comment(lib, "ws2_32.lib") // 链接Winsock库


// Function Prorotypes
s32 execute_adb_command(const char* command);
int send_zone_value(const s32 zone_value);
int send_switch_value(const s32 switch_value, const s32 keytime);
int send_switch_value_alltime(const s32 switch_value, const s32 enable_disable);
int CaptureScreenToBMP(const char* filename);
int NFCStrat(const char* name);
int deletevideo(const char* name);
int savevideo(const char* name);
int decrypt_wrapper(const unsigned char* key, const unsigned char* encrypted_data, unsigned char** decrypted_data);
int MachineArm_Rotation(const s32 angle);
int process_dbc(const char* filename, int target_id, int** illegal_data);
int command_withresult(const char* cmd);
int execute_serial_command(const char* port, const s32 baudrate, const char* command);
// Variables defintions
TMPVarInt NewVariable1;

// Timers defintions
TMPTimerMS NewTimer1;

// 主step函数，执行周期 500 ms
void step(void) { // 周期 = 500 ms
	log("step function every 500ms");
}

// CAN报文接收事件 "NewOn_CAN_Rx1" 针对标识符 = 0x123 (FD)
void on_canfd_rx_NewOn_CAN_Rx1(const PCANFD ACANFD) { // 针对标识符 = 0x123 (FD)
	log("CAN frame 0x123 has been received");
}

// CAN报文发送成功事件 "NewOn_CAN_Tx1" 针对标识符 = 0x123 (FD)
void on_canfd_tx_NewOn_CAN_Tx1(const PCANFD ACANFD) { // 针对标识符 = 0x123 (FD)
	log("CAN frame 0x123 has been transmitted successfully");
}

// CAN报文预发送事件 "NewOn_CAN_PreTx1" 针对标识符 = 0x123 (FD)
void on_canfd_pretx_NewOn_CAN_PreTx1(const PCANFD ACANFD) { // 针对标识符 = 0x123 (FD)
	log("CAN frame 0x123 is being transmitted, you can modify its content before sending out");
}

// LIN报文接收事件 "NewOn_LIN_Rx1" 针对标识符 = 0x12
void on_lin_rx_NewOn_LIN_Rx1(const PLIN ALIN) { // 针对标识符 = 0x12
	log("LIN frame 0x12 has been received");
}

// LIN报文发送成功事件 "NewOn_LIN_Tx1" 针对标识符 = 0x12
void on_lin_tx_NewOn_LIN_Tx1(const PLIN ALIN) { // 针对标识符 = 0x12
	log("LIN frame 0x12 has been transmitted successfully");
}

// LIN报文预发送事件 "NewOn_LIN_PreTx1" 针对标识符 = 0x12
void on_lin_pretx_NewOn_LIN_PreTx1(const PLIN ALIN) { // 针对标识符 = 0x12
	log("LIN frame 0x12 is being transmitted, you can modify its content before sending out");
}

// 变量变化事件 "NewOn_Var_Change1" 针对变量 "NewVariable1"
void on_var_change_NewOn_Var_Change1(void) { // 变量 = NewVariable1
	log("NewVariable1 has been changed to %d", NewVariable1.get());
}

// 定时器触发事件 "NewOn_Timer1" for Timer NewTimer1
void on_timer_NewOn_Timer1(void) { // 定时器 = NewTimer1
	log("Timer 100ms fired");
}

// 启动事件 "NewOn_Start1"
void on_start_NewOn_Start1(void) { // 程序启动事件
	log("TSMaster mini program is starting...");
	NewTimer1.start();
}

// 停止事件 "NewOn_Stop1"
void on_stop_NewOn_Stop1(void) { // 程序停止事件
	log("TSMaster mini program is stopped");
}

// 快捷键事件 "NewOn_Shortcut1" 快捷键 = Ctrl+R
void on_shortcut_NewOn_Shortcut1(const s32 AShortcut) { // 快捷键事件 = Ctrl+R
	log("You have pressed Ctrl + R short-cut key");
}

// 自定义函数 "func1"
s32 func1(const s32 A1, const s32 A2) { // 自定义函数
	log("Custom function is called with result = %d", A1 + A2);
	return A1 + A2;

}


s32 execute_adb_command(const char* command) {
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));

    // Create a modifiable command buffer
    char cmdBuffer[256];
    snprintf(cmdBuffer, sizeof(cmdBuffer), "cmd.exe /C \"%s\"", command);

    // Create the process
    if (!CreateProcessA(NULL,   // No module name (use command line)
        cmdBuffer,              // Command line
        NULL,                  // Process handle not inheritable
        NULL,                  // Thread handle not inheritable
        FALSE,                 // Set handle inheritance to FALSE
        CREATE_NO_WINDOW,      // No creation flags
        NULL,                  // Use parent's environment block
        NULL,                  // Use parent's starting directory 
        &si,                   // Pointer to STARTUPINFO structure
        &pi)                   // Pointer to PROCESS_INFORMATION structure
        ) {
        fprintf(stderr, "Command execution failed: %s\n", command);
        fprintf(stderr, "Error code: %lu\n", GetLastError());
        return -1;
    }

    // Wait until child process exits.
    WaitForSingleObject(pi.hProcess, INFINITE);

    // Close process and thread handles. 
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return 0;
}


int command_withresult(const char* cmd) {
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));

    HANDLE hReadPipe, hWritePipe;
    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE };
    if (!CreatePipe(&hReadPipe, &hWritePipe, &sa, 0)) {
        return -1;
    }

    si.hStdOutput = hWritePipe;
    si.hStdError = hWritePipe;

    if (!CreateProcessA(NULL, (char*)cmd, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(hReadPipe);
        CloseHandle(hWritePipe);
        return -1;
    }

    CloseHandle(hWritePipe);

    const int bufferSize = 8192;
    char* buffer = new char[bufferSize];
    DWORD bytesRead;
    std::string fullOutput;
    size_t prevLength = 0;
    bool foundResult = false;
    // 循环读取输出，只要进程还没结束就持续读取
    while (WaitForSingleObject(pi.hProcess, 0) == WAIT_TIMEOUT) {
        if (!ReadFile(hReadPipe, buffer, bufferSize - 1, &bytesRead, NULL) || bytesRead == 0) {
            if (bytesRead == 0 && GetLastError() == ERROR_BROKEN_PIPE) {
                continue;
            }
            CloseHandle(hReadPipe);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
            delete[] buffer;
            return -1;
        }
        buffer[bytesRead] = '\0';
        fullOutput.append(buffer, bytesRead);

        const char* resultStart = strstr(fullOutput.c_str(), "Function execution result: ");
        if (resultStart != nullptr) {
            resultStart += strlen("Function execution result: ");
            if (*resultStart == '0') {
                delete[] buffer;
                return 0;
            }
            else if (*resultStart == '1') {
                delete[] buffer;
                return 1;
            }
            foundResult = true;
            break;
        }
    }

    // 进程结束后，再读取剩余可能的输出内容（以防还有未读完的）
    do {
        if (!ReadFile(hReadPipe, buffer, bufferSize - 1, &bytesRead, NULL) || bytesRead == 0) {
            break;
        }
        buffer[bytesRead] = '\0';
        fullOutput.append(buffer, bytesRead);

        const char* resultStart = strstr(fullOutput.c_str(), "Function execution result: ");
        if (resultStart != nullptr) {
            resultStart += strlen("Function execution result: ");
            if (*resultStart == '0') {
                delete[] buffer;
                return 0;
            }
            else if (*resultStart == '1') {
                delete[] buffer;
                return 1;
            }
            foundResult = true;
            break;
        }
    } while (true);

    CloseHandle(hReadPipe);

    WaitForSingleObject(pi.hProcess, INFINITE);

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    if (!foundResult) {
        return -1;
    }

    delete[] buffer;
    return -1;
}


void error(const char* msg) {
    fprintf(stderr, "%s: %d\n", msg, WSAGetLastError());
    exit(1);
}

const char* server_ip = "192.168.1.1"; // 服务器IP地址  
int port = 2001; // 服务器端口  

int send_switch_value(const s32 switch_value, const s32 keytime) {
    WSADATA wsaData;
    SOCKET sockfd;
    struct sockaddr_in server_addr;
    int result;
    struct timeval tv;

    // 初始化Winsock  
    result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        printf("WSAStartup failed: %d\n", result);
        return 1;
    }

    // 创建套接字  
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == INVALID_SOCKET) {
        printf("socket failed: %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    // 填充服务器地址信息  
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    // 使用inet_pton转换字符串到网络字节序  
    struct in_addr server_ipv4;
    if (inet_pton(AF_INET, server_ip, &(server_ipv4.s_addr)) <= 0) {
        printf("inet_pton failed\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    server_addr.sin_addr = server_ipv4;

    // 连接服务器  
    result = connect(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr));
    if (result == SOCKET_ERROR) {
        printf("connect failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 构造发送的字节数组  
    unsigned char message[5] = { 0xFF, 0x05,switch_value,keytime/20, 0xFF }; // 假设zone_value是16位  

    // 发送数据  
    result = send(sockfd, (char*)message, sizeof(message), 0);
    if (result == SOCKET_ERROR) {
        printf("send failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 设置接收超时  
    // 设置接收超时  
    tv.tv_sec = 20; // 20秒  
    tv.tv_usec = 0;

    // 使用select来等待套接字上的可读事件
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(sockfd, &readfds);

    result = select(sockfd + 1, &readfds, NULL, NULL, &tv);
    if (result == 0) {
        // 超时，套接字在指定时间内没有变得可读
        printf("接收超时\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    else if (result == SOCKET_ERROR) {
        // select调用失败
        printf("select failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 如果select成功，套接字已经准备好读取
    if (FD_ISSET(sockfd, &readfds)) {
        // 接收数据...
    }

    // 注意：在Windows上，你应该使用setsockopt和SO_RCVTIMEO  
    result = setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));
    if (result == SOCKET_ERROR) {
        printf("setsockopt failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 接收数据  
    unsigned char received_data[5]; // 假设期望的响应是6个字节  
    int bytes_received = recv(sockfd, (char*)received_data, sizeof(received_data), 0);
    if (bytes_received == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error == WSAETIMEDOUT) {
            //printf("接收超时\n");
            // 接收超时  
            return 1;
        }
        else {
            //printf("其他错误\n");
            // 处理其他错误  
            return 1;
        }
    }
    //if (bytes_received > 0) {
    //    printf("接收到的数据: ");
    //    for (int i = 0; i < bytes_received; ++i) {
    //        printf("%02X ", received_data[i]); // 以十六进制格式打印每个字节
    //    }
    //    printf("\n");
    //}

    if (//bytes_received == 5 &&
        received_data[0] == 0xFF 
        //received_data[1] == 0x00 &&
        //received_data[2] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[3] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[4] == 0xFF
        ) {
        closesocket(sockfd);
        WSACleanup();
        //printf("成功接收到响应\n");
        return 0;
    }
    else {

        //printf("接收到的数据不符合预期格式\n");
        closesocket(sockfd);
        WSACleanup();
        // 接收到的数据不符合预期格式或字节数不正确  
        return 1;
    }
    closesocket(sockfd);
    WSACleanup();
    // 关闭套接字和Winsock  


    return 0; // 返回0表示程序成功执行
}

int send_switch_value_alltime(const s32 switch_value, const s32 enable_disable) {
    WSADATA wsaData;
    SOCKET sockfd;
    struct sockaddr_in server_addr;
    int result;
    struct timeval tv;

    // 初始化Winsock  
    result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        printf("WSAStartup failed: %d\n", result);
        return 1;
    }

    // 创建套接字  
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == INVALID_SOCKET) {
        printf("socket failed: %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    // 填充服务器地址信息  
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    // 使用inet_pton转换字符串到网络字节序  
    struct in_addr server_ipv4;
    if (inet_pton(AF_INET, server_ip, &(server_ipv4.s_addr)) <= 0) {
        printf("inet_pton failed\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    server_addr.sin_addr = server_ipv4;

    // 连接服务器  
    result = connect(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr));
    if (result == SOCKET_ERROR) {
        printf("connect failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 构造发送的字节数组  
    unsigned char message[5] = { 0xFF, 0x07,switch_value,enable_disable, 0xFF }; // 假设zone_value是16位  

    // 发送数据  
    result = send(sockfd, (char*)message, sizeof(message), 0);
    if (result == SOCKET_ERROR) {
        printf("send failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 设置接收超时  
    // 设置接收超时  
    tv.tv_sec = 20; // 20秒  
    tv.tv_usec = 0;

    // 使用select来等待套接字上的可读事件
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(sockfd, &readfds);

    result = select(sockfd + 1, &readfds, NULL, NULL, &tv);
    if (result == 0) {
        // 超时，套接字在指定时间内没有变得可读
        printf("接收超时\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    else if (result == SOCKET_ERROR) {
        // select调用失败
        printf("select failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 如果select成功，套接字已经准备好读取
    if (FD_ISSET(sockfd, &readfds)) {
        // 接收数据...
    }

    // 注意：在Windows上，你应该使用setsockopt和SO_RCVTIMEO  
    result = setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));
    if (result == SOCKET_ERROR) {
        printf("setsockopt failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 接收数据  
    unsigned char received_data[5]; // 假设期望的响应是6个字节  
    int bytes_received = recv(sockfd, (char*)received_data, sizeof(received_data), 0);
    if (bytes_received == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error == WSAETIMEDOUT) {
            //printf("接收超时\n");
            // 接收超时  
            return 1;
        }
        else {
            //printf("其他错误\n");
            // 处理其他错误  
            return 1;
        }
    }
    //if (bytes_received > 0) {
    //    printf("接收到的数据: ");
    //    for (int i = 0; i < bytes_received; ++i) {
    //        printf("%02X ", received_data[i]); // 以十六进制格式打印每个字节
    //    }
    //    printf("\n");
    //}

    if (//bytes_received == 5 &&
        received_data[0] == 0xFF
        //received_data[1] == 0x00 &&
        //received_data[2] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[3] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[4] == 0xFF
        ) {
        closesocket(sockfd);
        WSACleanup();
        //printf("成功接收到响应\n");
        return 0;
    }
    else {

        //printf("接收到的数据不符合预期格式\n");
        closesocket(sockfd);
        WSACleanup();
        // 接收到的数据不符合预期格式或字节数不正确  
        return 1;
    }
    closesocket(sockfd);
    WSACleanup();
    // 关闭套接字和Winsock  


    return 0; // 返回0表示程序成功执行
}

int send_zone_value(const s32 zone_value) {
    WSADATA wsaData;
    SOCKET sockfd;
    struct sockaddr_in server_addr;
    int result;
    struct timeval tv;

    // 初始化Winsock  
    result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        printf("WSAStartup failed: %d\n", result);
        return 1;
    }

    // 创建套接字  
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd == INVALID_SOCKET) {
        printf("socket failed: %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    // 填充服务器地址信息  
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    // 使用inet_pton转换字符串到网络字节序  
    struct in_addr server_ipv4;
    if (inet_pton(AF_INET, server_ip, &(server_ipv4.s_addr)) <= 0) {
        printf("inet_pton failed\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    server_addr.sin_addr = server_ipv4;

    // 连接服务器  
    result = connect(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr));
    if (result == SOCKET_ERROR) {
        printf("connect failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 构造发送的字节数组  
    unsigned char message[5] = { 0xFF, 0x06,zone_value, 0x00, 0xFF }; // 假设zone_value是16位  

    // 发送数据  
    result = send(sockfd, (char*)message, sizeof(message), 0);
    if (result == SOCKET_ERROR) {
        printf("send failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 设置接收超时  
    // 设置接收超时  
    tv.tv_sec = 120; // 20秒  
    tv.tv_usec = 0;

    // 使用select来等待套接字上的可读事件
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(sockfd, &readfds);

    result = select(sockfd + 1, &readfds, NULL, NULL, &tv);
    if (result == 0) {
        // 超时，套接字在指定时间内没有变得可读
        printf("接收超时\n");
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }
    else if (result == SOCKET_ERROR) {
        // select调用失败
        printf("select failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 如果select成功，套接字已经准备好读取
    if (FD_ISSET(sockfd, &readfds)) {
        // 接收数据...
    }

    // 注意：在Windows上，你应该使用setsockopt和SO_RCVTIMEO  
    result = setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));
    if (result == SOCKET_ERROR) {
        printf("setsockopt failed: %d\n", WSAGetLastError());
        closesocket(sockfd);
        WSACleanup();
        return 1;
    }

    // 接收数据  
    unsigned char received_data[5]; // 假设期望的响应是6个字节  
    int bytes_received = recv(sockfd, (char*)received_data, sizeof(received_data), 0);
    if (bytes_received == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error == WSAETIMEDOUT) {
            //printf("接收超时\n");
            // 接收超时  
            return 1;
        }
        else {
            //printf("其他错误\n");
            // 处理其他错误  
            return 1;
        }
    }
    //if (bytes_received > 0) {
    //    printf("接收到的数据: ");
    //    for (int i = 0; i < bytes_received; ++i) {
    //        printf("%02X ", received_data[i]); // 以十六进制格式打印每个字节
    //    }
    //    printf("\n");
    //}

    if (//bytes_received == 5 &&
        received_data[0] == 0xFF 
        //received_data[1] == 0x00 &&
        //received_data[2] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[3] == 0xFF && // 假设这不是响应的一部分，或者你可以根据需要调整  
        //received_data[4] == 0xFF
        ) {
        closesocket(sockfd);
        WSACleanup();
        //printf("成功接收到响应\n");
        return 0;
    }
    else {

        //printf("接收到的数据不符合预期格式\n");
        closesocket(sockfd);
        WSACleanup();
        // 接收到的数据不符合预期格式或字节数不正确  
        return 1;
    }
    closesocket(sockfd);
    WSACleanup();
    // 关闭套接字和Winsock  


    return 0; // 返回0表示程序成功执行
}


int CaptureScreenToBMP(const char* filename) {
    // 设置区域设置
    setlocale(LC_ALL, "");

    // 获取当前时间
    time_t now;
    struct tm timeinfo;
    time(&now);
    localtime_s(&timeinfo, &now);

    // 创建文件夹路径字符串，格式为 "D:\\ivi_test_log\\YYYYMMDD"
    wchar_t folder_path[MAX_PATH];
    swprintf(folder_path, MAX_PATH, L"D:\\dkc_test_log\\img\\%04d%02d%02d",
        timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday);

    // 检查文件夹是否存在，如果不存在则创建
    if (!CreateDirectory(folder_path, NULL) && GetLastError() != ERROR_ALREADY_EXISTS) {
        wprintf(L"无法创建文件夹: %ls\n", folder_path);
        return 1;
    }

    // 将char类型的filename转换为wchar_t类型
    wchar_t w_filename[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, filename, -1, w_filename, MAX_PATH);

    // 创建文件名字符串，格式为 "HHMMSS.bmp"
    wchar_t file_name[MAX_PATH];
    swprintf(file_name, MAX_PATH, L"%ls\\%s_%02d%02d%02d.bmp", folder_path, w_filename,
        timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);

    // 获取屏幕尺寸
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);

    // 获取桌面设备上下文
    HDC hScreenDC = GetDC(NULL);
    HDC hMemoryDC = CreateCompatibleDC(hScreenDC);
    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, screenWidth, screenHeight);
    SelectObject(hMemoryDC, hBitmap);

    // 复制屏幕到位图
    BitBlt(hMemoryDC, 0, 0, screenWidth, screenHeight, hScreenDC, 0, 0, SRCCOPY);

    // 保存位图到文件
    BITMAPFILEHEADER fileHeader;
    BITMAPINFOHEADER infoHeader;
    BITMAP bmpScreen;

    GetObject(hBitmap, sizeof(BITMAP), &bmpScreen);

    DWORD dwBmpSize = ((bmpScreen.bmWidth * bmpScreen.bmBitsPixel + 31) / 32) * 4 * bmpScreen.bmHeight;

    // 创建文件
    HANDLE hFile = CreateFile(file_name, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);

    // 设置位图文件头
    fileHeader.bfType = 0x4D42; // BM
    fileHeader.bfSize = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + dwBmpSize;
    fileHeader.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);

    infoHeader.biSize = sizeof(BITMAPINFOHEADER);
    infoHeader.biWidth = bmpScreen.bmWidth;
    infoHeader.biHeight = bmpScreen.bmHeight;
    infoHeader.biPlanes = 1;
    infoHeader.biBitCount = bmpScreen.bmBitsPixel;
    infoHeader.biCompression = BI_RGB;
    infoHeader.biSizeImage = 0;
    infoHeader.biXPelsPerMeter = 0;
    infoHeader.biYPelsPerMeter = 0;
    infoHeader.biClrUsed = 0;
    infoHeader.biClrImportant = 0;

    DWORD dwBytesWritten = 0;
    WriteFile(hFile, (LPSTR)&fileHeader, sizeof(BITMAPFILEHEADER), &dwBytesWritten, NULL);
    WriteFile(hFile, (LPSTR)&infoHeader, sizeof(BITMAPINFOHEADER), &dwBytesWritten, NULL);

    // 写入位图数据
    BYTE* lpBitmapData = new BYTE[dwBmpSize];
    GetDIBits(hScreenDC, hBitmap, 0, (UINT)bmpScreen.bmHeight, lpBitmapData, (BITMAPINFO*)&infoHeader, DIB_RGB_COLORS);
    WriteFile(hFile, lpBitmapData, dwBmpSize, &dwBytesWritten, NULL);

    // 清理
    delete[] lpBitmapData;
    CloseHandle(hFile);
    DeleteObject(hBitmap);
    DeleteDC(hMemoryDC);
    ReleaseDC(NULL, hScreenDC);
    return 0;
}

int testfunction()
{
    Sleep(120000);
    return 0;
}

void nfc()
{
    CURL* curl;
    CURLcode res;

    curl_global_init(CURL_GLOBAL_DEFAULT);

    curl = curl_easy_init();
    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, "http://192.168.2.1/command?NFCStart.txt&time=1708684897557");
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0");

        /* Perform the request, res will get the return code */
        res = curl_easy_perform(curl);
        /* Check for errors */
        if (res != CURLE_OK)
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));

        /* always cleanup */
        curl_easy_cleanup(curl);
    }

    curl_global_cleanup();

    return;
}

int MachineArm_Rotation(const s32 angle)
{
    if (angle < 0 || angle > 180) {
        return 1; // 角度不在范围内，返回1  
    }

    CURL* curl;
    CURLcode res;
    char url[100]; // 假设URL长度不会超过100个字符  

    curl_global_init(CURL_GLOBAL_DEFAULT);

    curl = curl_easy_init();
    if (curl) {
        // 构建URL字符串  
        snprintf(url, sizeof(url), "http://192.168.2.1/command?X%d", angle);
        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0");

        /* Perform the request, res will get the return code */
        res = curl_easy_perform(curl);
        /* Check for errors */
        if (res != CURLE_OK) {
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
            curl_easy_cleanup(curl);
            curl_global_cleanup();
            return -1; // 发生错误，返回-1  
        }

        /* always cleanup */
        curl_easy_cleanup(curl);
    }
    else {
        curl_global_cleanup();
        return -1; // curl初始化失败，返回-1  
    }

    curl_global_cleanup();

    return 0; // 成功执行，返回0  
}

void createFolderWithDate(const char* basePath) {
    struct tm current_time;
    time_t now = time(0);
    localtime_s(&current_time, &now); // 使用 localtime_s

    char folderName[100];
    strftime(folderName, sizeof(folderName), "%Y%m%d", &current_time);

    char fullPath[150];
    sprintf_s(fullPath, sizeof(fullPath), "%s//%s", basePath, folderName);

    // 检查文件夹是否存在
    struct stat st = { 0 };
    if (stat(fullPath, &st) == -1) {
        _mkdir(fullPath); // 如果不存在，则创建文件夹
    }
}

int NFCStrat(const char* name) {
    cv::VideoCapture capture(0); // 打开默认摄像头
    if (!capture.isOpened()) {
        std::cerr << "ERROR: 摄像头无法打开" << std::endl;
        return -1;
    }

    // 获取视频帧的宽度和高度
    int frame_width = static_cast<int>(capture.get(cv::CAP_PROP_FRAME_WIDTH));
    int frame_height = static_cast<int>(capture.get(cv::CAP_PROP_FRAME_HEIGHT));

    // 创建以今日日期命名的文件夹
    const char* basePath = "D://dkc_test_log//video";
    createFolderWithDate(basePath);

    // 获取今日日期文件夹的路径
    time_t now = time(0);
    struct tm current_time;
    localtime_s(&current_time, &now); // 使用 localtime_s
    char dateFolderName[100];
    strftime(dateFolderName, sizeof(dateFolderName), "%Y%m%d", &current_time);
    char dateFolderPath[150];
    sprintf_s(dateFolderPath, sizeof(dateFolderPath), "%s//%s", basePath, dateFolderName);

    const char* fileNumber = name;

    // 获取当前时间，用于文件命名
    char filename[100];
    strftime(filename, sizeof(filename), "%Y%m%d_%H%M%S.avi", &current_time);

    // 创建完整的文件名，格式为 "数字_当前时间.avi"
    char fullFilename[150];
    sprintf_s(fullFilename, sizeof(fullFilename), "%s//%s_%s", dateFolderPath, fileNumber, filename);

    // 创建视频写入对象，使用当前时间作为文件名
    cv::VideoWriter video(fullFilename, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'), 10, cv::Size(frame_width, frame_height));

    cv::Mat frame;
    int frame_count = 0;

    // 开始录制视频
    while (frame_count < 40) {
        capture >> frame; // 读取当前帧
        if (frame.empty()) {
            std::cerr << "ERROR: 帧捕获失败" << std::endl;
            break;
        }

        // 在录制到一半时执行刷NFC卡的动作
        if (frame_count == 5) {
            nfc();
        }

        video.write(frame); // 写入视频文件
        frame_count++;

        // 显示当前帧
        //cv::imshow("Recording...", frame);
        if (cv::waitKey(100) >= 0) break; // 等待100ms或按键退出
    }

    // 释放资源
    capture.release();
    video.release();
    cv::destroyAllWindows();

    return 0;
}

// 辅助函数：删除指定文件夹中以name开头的时间最近的一个文件
int deleteLatestFileWithName(const char* folderPath, const char* name) {
    DIR* dir;
    struct dirent* ent;
    char latestFilename[260] = { 0 };
    time_t latestTime = 0;

    if ((dir = opendir(folderPath)) != NULL) {
        // 遍历文件夹中的所有文件
        while ((ent = readdir(dir)) != NULL) {
            // 如果是文件且以name开头
            if (ent->d_type == DT_REG && strstr(ent->d_name, name) == ent->d_name) {
                struct stat fileInfo;
                char filePath[260];
                sprintf_s(filePath, sizeof(filePath), "%s//%s", folderPath, ent->d_name);

                if (stat(filePath, &fileInfo) == 0) {
                    // 比较时间，找到最新的文件
                    if (fileInfo.st_mtime > latestTime) {
                        latestTime = fileInfo.st_mtime;
                        strcpy_s(latestFilename, sizeof(latestFilename), filePath);
                    }
                }
            }
        }
        closedir(dir);
    }
    else {
        // 无法打开文件夹
        perror("");
        return -1;
    }

    // 如果找到了最新的文件，删除它
    if (latestTime != 0) {
        return remove(latestFilename);
    }

    return -1; // 如果没有找到文件，返回-1
}

// 删除指定文件夹中以name开头的时间最近的一个avi文件
int deletevideo(const char* name) {
    struct tm current_time;
    time_t now = time(0);
    localtime_s(&current_time, &now); // 使用 localtime_s 获取当前时间

    char dateFolderNameToday[100];
    strftime(dateFolderNameToday, sizeof(dateFolderNameToday), "%Y%m%d", &current_time); // 今天的日期

    // 获取昨天的日期
    time_t yesterday = now - (24 * 60 * 60);
    struct tm yesterday_time;
    localtime_s(&yesterday_time, &yesterday); // 使用 localtime_s 获取昨天的时间
    char dateFolderNameYesterday[100];
    strftime(dateFolderNameYesterday, sizeof(dateFolderNameYesterday), "%Y%m%d", &yesterday_time); // 昨天的日期

    char dateFolderPathToday[150];
    sprintf_s(dateFolderPathToday, sizeof(dateFolderPathToday), "%s//%s", "D://dkc_test_log//video", dateFolderNameToday);

    char dateFolderPathYesterday[150];
    sprintf_s(dateFolderPathYesterday, sizeof(dateFolderPathYesterday), "%s//%s", "D://dkc_test_log//video", dateFolderNameYesterday);

    // 删除今天和昨天日期文件夹中以name开头的时间最近的一个avi文件
    if (deleteLatestFileWithName(dateFolderPathToday, name) == 0) {
        return 0; // 如果今天的文件夹中找到并删除了文件，则返回
    }

    // 如果今天的文件夹中没有找到，尝试昨天的文件夹
    return deleteLatestFileWithName(dateFolderPathYesterday, name);
}

// 辅助函数：修改指定文件夹中以name开头的时间最近的一个文件的名称
int renameLatestFileWithPrefix(const char* folderPath, const char* name) {
    DIR* dir;
    struct dirent* ent;
    char latestFilename[260] = { 0 };
    time_t latestTime = 0;

    if ((dir = opendir(folderPath)) != NULL) {
        // 遍历文件夹中的所有文件
        while ((ent = readdir(dir)) != NULL) {
            // 如果是文件且以name开头
            if (ent->d_type == DT_REG && strstr(ent->d_name, name) == ent->d_name) {
                struct stat fileInfo;
                char filePath[260];
                sprintf_s(filePath, sizeof(filePath), "%s\\%s", folderPath, ent->d_name);

                if (stat(filePath, &fileInfo) == 0) {
                    // 比较时间，找到最新的文件
                    if (fileInfo.st_mtime > latestTime) {
                        latestTime = fileInfo.st_mtime;
                        strcpy_s(latestFilename, sizeof(latestFilename), filePath);
                    }
                }
            }
        }
        closedir(dir);
    }
    else {
        // 无法打开文件夹
        perror("fuck");
        return -1;
    }

    // 如果找到了最新的文件，修改它的名称
    if (latestTime != 0) {
        char* filenamePointer = strrchr(latestFilename, '\\');
        if (filenamePointer != NULL) {
            // 构建新文件名时，确保使用 latestFilename 中保存的最新文件名
            char newFilename[260];
            sprintf_s(newFilename, sizeof(newFilename), "%s\\Fail_%s", folderPath, filenamePointer + 1);
            return rename(latestFilename, newFilename);
        }
        else {
            // 如果 strrchr 返回了 NULL，说明没有找到 '\\' 字符
            return -1;
        }
    }

    return -1; // 如果没有找到文件，返回-1
}

// 修改指定文件夹中以name开头的时间最近的一个avi文件的名称，在开头加上"Fail"
int savevideo(const char* name) {
    struct tm current_time;
    time_t now = time(0);
    localtime_s(&current_time, &now); // 使用 localtime_s 获取当前时间

    char dateFolderNameToday[100];
    strftime(dateFolderNameToday, sizeof(dateFolderNameToday), "%Y%m%d", &current_time); // 今天的日期

    // 获取昨天的日期
    time_t yesterday = now - (24 * 60 * 60);
    struct tm yesterday_time;
    localtime_s(&yesterday_time, &yesterday); // 使用 localtime_s 获取昨天的时间
    char dateFolderNameYesterday[100];
    strftime(dateFolderNameYesterday, sizeof(dateFolderNameYesterday), "%Y%m%d", &yesterday_time); // 昨天的日期
    char dateFolderPathToday[150];
    sprintf_s(dateFolderPathToday, sizeof(dateFolderPathToday), "%s\\%s", "D:\\dkc_test_log\\video", dateFolderNameToday);
    char dateFolderPathYesterday[150];
    sprintf_s(dateFolderPathYesterday, sizeof(dateFolderPathYesterday), "%s\\%s", "D:\\dkc_test_log\\video", dateFolderNameYesterday);
    // 修改今天和昨天日期文件夹中以name开头的时间最近的一个avi文件的名称
    if (renameLatestFileWithPrefix(dateFolderPathToday, name) == 0) {
        return 0; // 如果今天的文件夹中找到并修改了文件，则返回
    }

    // 如果今天的文件夹中没有找到，尝试昨天的文件夹
    return renameLatestFileWithPrefix(dateFolderPathYesterday, name);
}



// 解密函数
unsigned char* decrypt(const unsigned char* key, const unsigned char* encrypted_data) {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        fprintf(stderr, "Failed to create context\n");
        return NULL;
    }

    if (EVP_DecryptInit_ex(ctx, EVP_aes_128_ecb(), NULL, key, NULL) != 1) {
        fprintf(stderr, "Failed to initialize decryption\n");
        EVP_CIPHER_CTX_free(ctx);
        return NULL;
    }

    // 禁用填充
    EVP_CIPHER_CTX_set_padding(ctx, 0);

    unsigned char* decrypted_data = (unsigned char*)malloc(16 + 1); // 16 字节数据 + 1 字节终止符
    if (!decrypted_data) {
        fprintf(stderr, "Failed to allocate memory\n");
        EVP_CIPHER_CTX_free(ctx);
        return NULL;
    }

    int len;
    if (EVP_DecryptUpdate(ctx, decrypted_data, &len, encrypted_data, 16) != 1) {
        fprintf(stderr, "Failed to decrypt data\n");
        EVP_CIPHER_CTX_free(ctx);
        free(decrypted_data);
        return NULL;
    }

    int padding_len;
    if (EVP_DecryptFinal_ex(ctx, decrypted_data + len, &padding_len) != 1) {
        fprintf(stderr, "Failed to finalize decryption\n");
        ERR_print_errors_fp(stderr); // 打印错误信息
        EVP_CIPHER_CTX_free(ctx);
        free(decrypted_data);
        return NULL;
    }

    len += padding_len;
    decrypted_data[len] = '\0'; // 添加字符串终止符

    EVP_CIPHER_CTX_free(ctx);
    return decrypted_data;
}

int decrypt_wrapper(const unsigned char* key, const unsigned char* encrypted_data, unsigned char** decrypted_data) {
    *decrypted_data = decrypt(key, encrypted_data);
    return (*decrypted_data != NULL) ? 0 : -1; // 返回 0 表示成功，-1 表示失败
}

#define MAX_SIGNALS 100

typedef struct {
    int start_bit;
    int length;
} Signal;

typedef struct {
    int id;
    int size;
    Signal signals[MAX_SIGNALS];
    int signal_count;
} Message;

void parse_dbc_line(char* line, Message* message) {
    if (strncmp(line, "BO_", 3) == 0) {
        sscanf_s(line, "BO_ %d", &message->id);
        sscanf_s(strstr(line, ":") + 1, "%d", &message->size);
        message->signal_count = 0;
    }
    else if (strncmp(line, " SG_", 4) == 0) {
        Signal signal;
        sscanf_s(line, " SG_ %*s : %d|%d", &signal.start_bit, &signal.length);
        message->signals[message->signal_count++] = signal;
    }
}

void calculate_signal_bits(int start_bit, int signal_length, int* bits) {
    int start_byte = start_bit / 8;
    int start_bit_in_byte = start_bit % 8;
    int remaining_bits = signal_length;

    for (int byte = start_byte; remaining_bits > 0; byte++) {
        int start = (byte == start_byte) ? start_bit_in_byte : 7;
        int end = (remaining_bits > (start + 1)) ? 0 : (start - remaining_bits + 1);
        for (int bit = start; bit >= end; bit--) {
            bits[byte * 8 + bit] = 1;
        }
        remaining_bits -= (start - end + 1);
    }
}

void calculate_bits(Message* message, int* occupied_bits, int* unoccupied_bits, int* bits) {
    for (int i = 0; i < message->signal_count; i++) {
        Signal signal = message->signals[i];
        calculate_signal_bits(signal.start_bit, signal.length, bits);
    }
    *occupied_bits = 0;
    *unoccupied_bits = 0;
    for (int i = 0; i < message->size * 8; i++) {
        if (bits[i]) {
            (*occupied_bits)++;
        }
        else {
            (*unoccupied_bits)++;
        }
    }
}

int generate_random_array(int size, int* bits, int* illegal_data) {
    int has_one = 0;
    unsigned int seed;

    // 使用高分辨率计时器作为种子
    LARGE_INTEGER li;
    QueryPerformanceCounter(&li);
    seed = (unsigned int)li.QuadPart;
    srand(seed);

    for (int i = 0; i < size; i++) {
        illegal_data[i] = rand() % 256; // 生成0-255之间的随机数
    }

    // 确保随机数组与未占用位所对应的位至少有一位是1
    for (int i = 0; i < size * 8; i++) {
        if (!bits[i] && ((illegal_data[i / 8] & (1 << (i % 8))) != 0)) {
            has_one = 1;
            break;
        }
    }

    if (!has_one) {
        // 如果没有未占用位为0，则随机选择一个未占用位设置为1
        for (int i = 0; i < size * 8; i++) {
            if (!bits[i]) {
                illegal_data[i / 8] |= (1 << (i % 8));
                break;
            }
        }
    }

    return 0;
}

int process_dbc(const char* filename, int target_id, int** illegal_data) {
    FILE* file;
    fopen_s(&file, filename, "r");
    if (!file) {
        perror("Failed to open file");
        return 1;
    }

    char line[256];
    Message message;
    int occupied_bits, unoccupied_bits;
    int* bits = NULL;
    int found_target = 0;

    while (fgets(line, sizeof(line), file)) {
        if (strncmp(line, "BO_", 3) == 0) {
            if (found_target) {
                // 计算并打印结果
                bits = (int*)calloc(message.size * 8, sizeof(int));
                calculate_bits(&message, &occupied_bits, &unoccupied_bits, bits);
                /*printf("Message ID: %d\n", message.id);
                printf("Occupied bits: %d\n", occupied_bits);
                printf("Unoccupied bits: %d\n", unoccupied_bits);*/
                if (unoccupied_bits == 0) {
                    free(bits);
                    fclose(file);
                    return 1;
                }
                *illegal_data = (int*)malloc(message.size * sizeof(int));
                generate_random_array(message.size, bits, *illegal_data);
                free(bits);
                break;
            }
            parse_dbc_line(line, &message);
            if (message.id == target_id) {
                found_target = 1;
            }
        }
        else if (found_target && strncmp(line, " SG_", 4) == 0) {
            parse_dbc_line(line, &message);
        }
        else if (found_target && strncmp(line, " SG_", 4) != 0) {
            // 计算并打印结果
            bits = (int*)calloc(message.size * 8, sizeof(int));
            calculate_bits(&message, &occupied_bits, &unoccupied_bits, bits);
          /*  printf("Message ID: %d\n", message.id);
            printf("Occupied bits: %d\n", occupied_bits);
            printf("Unoccupied bits: %d\n", unoccupied_bits);*/
            if (unoccupied_bits == 0) {
                free(bits);
                fclose(file);
                return 1;
            }
            *illegal_data = (int*)malloc(message.size * sizeof(int));
            generate_random_array(message.size, bits, *illegal_data);
            free(bits);
            break;
        }
    }

    fclose(file);
    return 0;
}

int execute_serial_command(const char* port, const s32 baudrate, const char* command) {
    HANDLE hSerial;
    DCB dcbSerialParams = {0};
    COMMTIMEOUTS timeouts = {0};
    char portName[16];
    sprintf_s(portName, sizeof(portName), "\\\\.\\%s", port);  // Windows 串口命名

    // 打开串口
    hSerial = CreateFileA(portName,
        GENERIC_READ | GENERIC_WRITE,
        0,
        NULL,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        NULL);

    if (hSerial == INVALID_HANDLE_VALUE) {
        log("Error opening serial port %s: %d", port, GetLastError());
        return -1;
    }

    // 获取当前 DCB 设置
    GetCommState(hSerial, &dcbSerialParams);

    // 设置波特率和其他参数
    dcbSerialParams.BaudRate = baudrate;
    dcbSerialParams.ByteSize = 8;
    dcbSerialParams.StopBits = ONESTOPBIT;
    dcbSerialParams.Parity = NOPARITY;

    // 设置 DCB
    if (!SetCommState(hSerial, &dcbSerialParams)) {
        log("Error setting serial port parameters: %d", GetLastError());
        CloseHandle(hSerial);
        return -1;
    }

    // 设置超时
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    timeouts.WriteTotalTimeoutConstant = 50;
    timeouts.WriteTotalTimeoutMultiplier = 10;

    if (!SetCommTimeouts(hSerial, &timeouts)) {
        log("Error setting timeouts: %d", GetLastError());
        CloseHandle(hSerial);
        return -1;
    }

    // 发送指令，添加回车键
    char temp[256];
    if (strlen(command) >= sizeof(temp) - 2) {
        log("Command too long for serial port");
        CloseHandle(hSerial);
        return -1;
    }
    strcpy_s(temp, sizeof(temp), command);
    strcat_s(temp, sizeof(temp), "\r");
    DWORD bytesWritten;
    if (!WriteFile(hSerial, temp, (DWORD)strlen(temp), &bytesWritten, NULL)) {
        log("Error writing to serial port: %d", GetLastError());
        CloseHandle(hSerial);
        return -1;
    }

    // 简单等待并读取响应
    Sleep(100);  // 等待响应

    char buffer[256];
    DWORD bytesRead;
    if (!ReadFile(hSerial, buffer, sizeof(buffer) - 1, &bytesRead, NULL)) {
        log("Error reading from serial port: %d", GetLastError());
    } else {
        buffer[bytesRead] = '\0';
        log("Serial response from %s: %s", port, buffer);
    }

    CloseHandle(hSerial);
    log("Serial command executed successfully on %s at %d baud", port, baudrate);
    return 0;
}