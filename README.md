# Linker

![Python](https://img.shields.io/badge/Python-3776AB?style=plastic&logo=python&logoColor=white&labelColor=555555)
![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=plastic&logo=apache&logoColor=white&labelColor=555555)
![Build](https://img.shields.io/badge/Build-passing-brightgreen?style=plastic&labelColor=555555)
![Android](https://img.shields.io/badge/Android-3DDC84?style=plastic&logo=android&logoColor=white&labelColor=555555)
![Tests](https://img.shields.io/badge/Tests-passing-brightgreen?style=plastic&labelColor=555555)

**Linker is a command line tool that collects HTTP and HTTPS links from the web based on a keyword provided by the user.**

The user enters a keyword and a target number of links. Linker searches **Bing** and **Baidu** for that keyword, extracts every `HTTP` and `HTTPS` link it finds in the results, removes duplicates, and stops once the requested number of links has been reached. All collected links are then written to a plain text file on the device.

**Linker** is designed to run on **Termux** and requires **no third party libraries.**

# How to Run

**Step 1**
Install Termux on your Android device.

**Step 2**
Open Termux and run the following command once to grant storage access.

```bash
termux-setup-storage
```

**Step 3**
Save the Linker script to your Termux home directory.

**Step 4**
Run the script with Python.

```Python
python3 Linker.py
```

**Step 5**
When prompted, enter the keyword you want to search for.

**Step 6**
When prompted, enter the number of links you want to collect.

**Step 7**
Wait for Linker to finish. Progress and the final status are printed on the screen.

**Step 8**
Open the output file to view the collected links.

`/storage/emulated/0/MT2/URL.txt`

# Output

The result is a plain text file named **URL.txt** located in the `/storage/emulated/0/MT2` folder on your device storage. Each line contains one unique `HTTP` or `HTTPS` link.

# License
**Apache License 2.0**

# Notes

Linker only collects `HTTP` and `HTTPS` links. It does not download any content. It does not follow links beyond the search result pages. Duplicate links are removed automatically. The number of collected links never exceeds the value entered by the user.
