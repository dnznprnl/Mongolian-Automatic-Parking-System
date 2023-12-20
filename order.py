import os

directory_path = r'C:\Users\Pc\Desktop\haarcascade\p'

files = os.listdir(directory_path)

files.sort()

for index, file_name in enumerate(files, start=1):
    new_file_name = str(index) + os.path.splitext(file_name)[1]

    old_path = os.path.join(directory_path, file_name)
    new_path = os.path.join(directory_path, new_file_name)

    os.rename(old_path, new_path)
