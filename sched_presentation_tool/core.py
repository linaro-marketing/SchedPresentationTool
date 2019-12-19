from urllib import request
import urllib.parse
import os
import re
import requests
from requests.utils import requote_uri

import json
# Import the API_KEY variable
# Your API_KEY can be fetched from the https://event_name.sched.com/editor/exports/api
from secrets import SCHED_API_KEY


class SchedPresentationTool:

    """
    This class grabs presentations and other files from the Sched Event Export api
    and then downloads and modifies the resources.json file for the current Connect and
    uploads newly retreived presentations/files. This should be run daily at the least.
    """

    def __init__(self, sched_url=None, connect_code="bkk19"):

        # Verbose output toggle
        self._verbose = False
        # Current Connect Code
        self.connect_code = connect_code
        # Sched.com url
        self.sched_url = sched_url
        # Sched.com API Key
        self.API_KEY = SCHED_API_KEY
        # Location of posts
        self._download_location = connect_code + "/"
        # Blacklisted tracks to ignore when creating pages/resources.json
        self.blacklistedTracks = ["Food & Beverage", "Informational"]
        # Main Method
        self.main()

    def main(self):
        """
        Main method for the JekyllSchedExportTool
        """
        # Get the results from sched api
        self.export_data = self.get_api_results(
            "/api/session/export?api_key={0}&format=json&fields=event_key,event_type,active,name,id,files,speakers")
        # Download to pdfs/other files for each session in sched.com
        self.users_data = self.get_api_results(
            "/api/user/list?api_key={0}&format=json")
        # Download for details pdfs/other files in each session in sched.com
        sessions_data = self.download_session_files(self.export_data)

    def get_api_results(self, endpoint):
        """
            Gets the results from a specified endpoint
        """
        endpoint = self.sched_url + endpoint.format(self.API_KEY)
        if self._verbose:
            print("Fetch data from: {} ".format(endpoint))
        try:
            resp = requests.get(url=endpoint)
            data = resp.json()
            return data
        except Exception as e:
            print(e)
            return False

    def download_session_files(self, export_data):
        """
        This method grabs the files/session_id's for each session and updates the resources.json file
        in s3.
        """
        self.missing_presentations = []
        sessions = []
        for session in export_data:
            # Get the title of the session - to retrieve the session ID.
            session_title = session["name"]
            # Fetch the main session track.
            try:
                session_track = session["event_type"]
            except Exception as e:
                if self._verbose:
                    print(e)
                session_track = None
            # Check the current track is not in the blacklisted tracks
            if session_track not in self.blacklistedTracks:
                # Get the session id from the title
                try:
                    # Compile the session ID regex
                    session_id_regex = re.compile(
                        '{}-[A-Za-z]*[0-9]+K*[0-9]*'.format(self.connect_code.upper()))
                    # Get the first item found based on the regex
                    session_id = session_id_regex.findall(session_title)[0]
                    # Set skipping to False so the script continues
                    skipping = False
                # If no session ID exists then skip the session and output a warning
                except Exception as e:
                    if self._verbose:
                        print("Error when fetching the session ID for {}".format(
                            session_title), e)
                    skipping = True
            else:
                skipping = True
            # Check to see if we should continue and download the presentations.
            if skipping == False:
                print("{}: ".format(session_id), end="", flush=True)
                # Create a new dict for updating the resources.json file with other_files list
                resources_session_data = {
                    "session_id": session_id,
                    "other_files": ""
                }
                try:
                    if session["files"]:
                        # Create a new other_files list for storing the non-pdf files
                        other_files = []
                        found_pdf = False
                        # Loop over all the files for this session
                        for session_file in session["files"]:
                            # Check if the file name endswith .pdf
                            if session_file["name"].endswith(".pdf"):
                                # Set output folder to presentations/
                                output_folder = "presentations/"
                                output_filename = session_id.lower() + ".pdf"
                                found_pdf = True
                                print("P", end="", flush=True)
                            # File is not a pdf so add to the other files array
                            else:
                                # Change the output folder for syncing to the other files folder on s3
                                output_folder = "other_files/"
                                # Add output folder to output path - prepend the session_id as a unique identifier
                                # All files are stored in the same bucket so if two users upload a file named presentation.pptx
                                # then one would write over the other.
                                output_filename = "{0}-{1}".format(
                                    session_id, session_file["name"])
                                # Append the new file to the other files array
                                other_files.append(output_filename)
                                print("O", end="", flush=True)

                            # Download the file
                            downloaded = self.grab_file(
                                session_id, session_file["path"], output_filename, output_folder)

                        if found_pdf == False:
                            try:
                                speakers = session["speakers"]
                            except Exception as e:
                                speakers = None
                            if speakers != None:
                                speakers = self.getDetailedSpeakers(speakers)


                        # Set the other files key to the array of other files
                        resources_session_data["other_files"] = other_files
                    # Add to main list of sessions to update resources.json with.
                    sessions.append(resources_session_data)
                except KeyError:
                    try:
                        speakers = session["speakers"]
                    except Exception as e:
                        speakers = None
                    if speakers != None:
                        speakers = self.getDetailedSpeakers(speakers)
                    print("X", end="", flush=True)
                print("",flush=True)

        return sessions

    def getDetailedSpeakers(self, speakers):
        """
        Gets detailed speakers array
        """
        try:
            for speaker in speakers:
                for user in self.users_data:
                    if speaker["username"] == user["username"]:
                        speaker["email"] = user["email"]
            return speakers
        except KeyError:
            return "Invalid"

    def grab_file(self, session_id, url, output_filename, output_path="speaker_images/"):
        """
        Fetches attendee photo from the pathable data
        """
        # Check to see if the output folder exists and create if not.
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        # Compose the output file path + filename
        output = output_path + output_filename
        # Encode the url
        encoded_url = requote_uri(url)
        # Try to download the image and Except errors and return as false.
        try:
            opener = request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            request.install_opener(opener)
            # Check to see if the file exists locally.
            if not os.path.exists(output):
                download_file = request.urlretrieve(encoded_url, output)
                if self._verbose:
                    print("Downloaded {}".format(
                        output_filename), download_file)
            # If file exists compare local file size with remote file size before downloading again
            else:
                header_check_request = request.urlopen(encoded_url)
                # Get size of remote file
                server_size = header_check_request.headers['Content-Length']
                # Get size of local file
                local_size = os.path.getsize(output)
                if self._verbose:
                    print("Comparing filesize: {0}B vs {1}B".format(local_size, server_size))
                # Check to see if file size differs and if it does - download the updated file
                if int(server_size) != int(local_size):
                    if self._verbose:
                        print(
                            "Downloading updated presentation for {0}".format(session_id))
                    download_file = request.urlretrieve(encoded_url, output)
                # If matches file size on server then do nothing but output a warning if verbose
                else:
                    # check difference between two files
                    if self._verbose:
                        print("Skipping download for {0}".format(
                            output_filename))
            return True
        except Exception as e:
            print(e)
            return False


if __name__ == "__main__":

    presentations = SchedPresentationTool(
        "https://linaroconnectsandiego.sched.com", "san19")
