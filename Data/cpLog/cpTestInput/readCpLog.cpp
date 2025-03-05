#include <iostream>
#include <fstream>
#include <string>
#include <regex>
#include <unordered_map>
#include <vector>

int main() {
    std::ifstream inputFile("instance3log.txt"); // �򿪰����ı����ļ�instance3log.txt
    std::ofstream outputFile("testNote.txt"); // �����������������ļ�output.txt
    std::string line;
    std::regex pattern("��ǰʱ��Ϊ:(\\d+\\.\\d+)��ǰĿ��ֵΪ(\\d+) ��ǰĿ��ֵ��GapΪ(\\d+\\.\\d+)"); // ƥ��ʱ�䡢Ŀ��ֵ��Gapֵ��������ʽ
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

        // ������һ������
        if (!currentInstance.empty()) {
            outputFile << currentInstance << " " << extractedData[currentInstance].first << " ";
            for (double gap : extractedData[currentInstance].second) {
                outputFile << gap << " ";
            }
            outputFile << std::endl;
        }

        inputFile.close();
        outputFile.close();
        std::cout << "��ȡ�������ɡ�" << std::endl;
    }
    else {
        std::cerr << "�޷����ļ���" << std::endl;
    }

    return 0;
}