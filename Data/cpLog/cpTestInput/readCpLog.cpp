#include <iostream>
#include <fstream>
#include <string>
#include <regex>
#include <unordered_map>
#include <vector>

int main() {
    std::ifstream inputFile("instance3log.txt"); // 打开包含文本的文件instance3log.txt
    std::ofstream outputFile("testNote.txt"); // 创建用于输出结果的文件output.txt
    std::string line;
    std::regex pattern("当前时间为:(\\d+\\.\\d+)当前目标值为(\\d+) 当前目标值的Gap为(\\d+\\.\\d+)"); // 匹配时间、目标值和Gap值的正则表达式
    std::unordered_map<std::string, std::pair<int, std::vector<double>>> extractedData;

    std::string currentInstance;

    if (inputFile.is_open() && outputFile.is_open()) {
        while (std::getline(inputFile, line)) {
            std::smatch match;
            if (std::regex_search(line, match, pattern)) {
                std::string instance = "instance" + match[2].str();
                double gapValue = std::stod(match[3].str());

                if (instance != currentInstance) {
                    if (!currentInstance.empty()) {
                        outputFile << currentInstance << " " << extractedData[currentInstance].first << " ";
                        for (double gap : extractedData[currentInstance].second) {
                            outputFile << gap << " ";
                        }
                        outputFile << std::endl;
                    }

                    currentInstance = instance;
                    extractedData[currentInstance] = std::make_pair(0, std::vector<double>());
                }

                extractedData[currentInstance].first++;
                extractedData[currentInstance].second.push_back(gapValue);
            }
        }

        // 输出最后一组数据
        if (!currentInstance.empty()) {
            outputFile << currentInstance << " " << extractedData[currentInstance].first << " ";
            for (double gap : extractedData[currentInstance].second) {
                outputFile << gap << " ";
            }
            outputFile << std::endl;
        }

        inputFile.close();
        outputFile.close();
        std::cout << "提取并输出完成。" << std::endl;
    }
    else {
        std::cerr << "无法打开文件。" << std::endl;
    }

    return 0;
}