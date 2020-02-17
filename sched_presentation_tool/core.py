from urllib import request
import urllib.parse
import os
import re
import requests
from requests.utils import requote_uri
from sched_data_interface import SchedDataInterface
import json

class SchedPresentationTool:

    """
    This class downloads new presentations and other files from the Sched Event API
    using the provided json_data.
    """

    def __init__(self, presentations_directory, other_files_directory, json_data):

        self.presentations_directory = presentations_directory
        if not os.path.exists(self.presentations_directory):
            os.makedirs(self.presentations_directory)
        self.other_files_directory = other_files_directory
        if not os.path.exists(self.other_files_directory):
            os.makedirs(self.other_files_directory)

        self.json_data = json_data

    def download(self):
        """
        This method grabs the files/session_id's for each session and updates the resources.json file
        in s3.
        """
        all_files = []
        print("Downloading session files...")
        for session in self.json_data.values():
            try:
                for session_file_index in range(0, len(session["files"])):
                    file_path = session["files"][session_file_index]["path"]
                    file_name = session["files"][session_file_index]["name"]
                    output_file_name = ""
                    output_folder = ""
                    if ".pdf" in file_name:
                        output_file_name = "{}-{}.pdf".format(session["session_id"], session_file_index)
                        output_folder = self.presentations_directory
                    else:
                        file_extension = os.path.splitext(file_name)[1]
                        output_file_name = "{}-{}{}".format(session["session_id"], session_file_index, file_extension)
                        output_folder = self.other_files_directory
                    # Download the file
                    all_files.append(output_file_name)
                    status = self.download_file(file_path, output_folder, output_file_name)
                    if status == "downloaded":
                        print("Downloaded {} to {}...".format(output_file_name, output_folder))
                    elif status == "updated":
                        print("Downloaded updated file {} to {}...".format(
                            output_file_name, output_folder))
                    elif status == "skipped":
                        print("Skipped download of {} to {} as there was no change...".format(output_file_name, output_folder))
                    else:
                        print("Download for {} to {} has failed...".format(output_file_name, output_folder))
            except Exception as e:
                pass
        print("Removing old presentations...")
        self.remove_old_files(self.presentations_directory, all_files)
        print("Removing old other_files...")
        self.remove_old_files(self.other_files_directory, all_files)

    def remove_old_files(self, folder, all_files_list):
        changed = False
        for file_name in os.listdir(folder):
            if file_name not in all_files_list:
                file_path = os.path.join(folder, file_name)
                os.remove(file_path)
                print("Deleted {}...".format(file_path))
                changed = True
        if not changed:
            print("No files to delete.")
        return True


    def download_file(self, file_url, output_folder, output_filename):
        """
        Fetches attendee photo from the pathable data
        """
        # Download pdf presentations
        # Compose the output file path + filename
        output = output_folder + output_filename
        # Encode the url
        encoded_url = requote_uri(file_url)
        # Try to download the image and Except errors and return as false.
        try:
            opener = request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            request.install_opener(opener)
            # Check to see if the file exists locally.
            if not os.path.exists(output):
                download_file = request.urlretrieve(encoded_url, output)
                status = "downloaded"
            # If file exists compare local file size with remote file size before downloading again
            else:
                header_check_request = request.urlopen(encoded_url)
                # Get size of remote file
                server_size = header_check_request.headers['Content-Length']
                # Get size of local file
                local_size = os.path.getsize(output)
                # Check to see if file size differs and if it does - download the updated file
                if int(server_size) != int(local_size):
                    download_file = request.urlretrieve(encoded_url, output)
                    status = "updated"
                # If matches file size on server then do nothing but output a warning if verbose
                else:
                    # check difference between two files
                    status = "skipped"
            return status
        except Exception as e:
            print(e)
            status = "failed"
            return status
