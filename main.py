from urllib import request
import os
import re
import requests
import json
# Import the API_KEY variable
# Your API_KEY can be fetched from the https://event_name.sched.com/editor/exports/api
from secrets import SCHED_API_KEY
from googlesheet import GoogleSheetAPI

class SchedPresentationExportTool:

    """
    This class grabs presentations and other files from the Sched Event Export api
    and then downloads and modifies the resources.json file for the current Connect and
    uploads newly retreived presentations/files. This should be run daily at the least.
    """

    def __init__(self, sched_url=None, connect_code="bkk19"):

        # Verbose output toggle
        self._verbose = True
        # Current Connect Code
        self.connect_code = connect_code
        # Sched.com url
        self.sched_url = sched_url
        # Sched.com API Key
        self.API_KEY = SCHED_API_KEY
        # Location of posts
        self._download_location = connect_code + "/"
        # Blacklisted tracks to ignore when creating pages/resources.json
        self.blacklistedTracks =  ["Food & Beverage","Informational"]
        # Googlesheet API Instance
        self.googlesheet = GoogleSheetAPI(True)
        # Main Method
        self.main()

    def main(self):
        """
        Main method for the JekyllSchedExportTool
        """
        # Get the results from sched api
        self.export_data = self.get_api_results("/api/session/export?api_key={0}&format=json&fields=event_key,event_type,active,name,id,files,speakers")
        # Download to pdfs/other files for each session in sched.com
        self.users_data = self.get_api_results("/api/user/list?api_key={0}&format=json")
        # Download for details pdfs/other files in each session in sched.com
        sessions_data = self.download_session_files(self.export_data)
        # Download/update the resources.json file
        self.update_resources_json_file(sessions_data)

    def update_resources_json_file(self, sessions_data):
        """
        This method downloads the resources.json file and updates with other_files list.
        """
        print("Downloading the resources.json file...")
        try:
            download_file = request.urlretrieve("https://s3.amazonaws.com/connect.linaro.org/{}/resources.json".format(self.connect_code), "resources.json")
            print("resources.json file downloaded successfully.")
        except Exception as e:
            print("An error has occured", e)
        print("Modifying the resources.json file with the sessions_data")
        with open("resources.json", "r") as resourcesFile:
            resourcesJson = json.load(resourcesFile)

        for session in sessions_data:
            if session["other_files"] != "" or len(session["other_files"]) > 0:
                for entry in resourcesJson:
                    if entry["session_id"] == session["session_id"]:
                        entry["other_files"] = session["other_files"]
                        print("Updated the other files for {}".format(session["session_id"]))

        with open("resources.json", "w") as updatedResourcesFile:
            updatedResourcesFile.writelines(json.dumps(resourcesJson))

        print("Other_files values updated in resources.json.")
        print("Please upload the file to s3 using the command below:")
        print("aws s3 --profile connect-linaro-org-Owner cp resources.json s3://connect.linaro.org/{}/resources.json".format(self.connect_code))
        input("Press enter to continue...")

        return True
    def get_api_results(self, endpoint):
        """
            Gets the results from a specified endpoint
        """
        endpoint = self.sched_url + endpoint.format(self.API_KEY)
        print(endpoint)
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
        self.missing_presentations =  []
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
                    session_id_regex = re.compile('SAN19-[A-Za-z]*[0-9]+K*[0-9]*')
                    # Get the first item found based on the regex
                    session_id = session_id_regex.findall(session_title)[0]
                    # Set skipping to False so the script continues
                    skipping = False
                # If no session ID exists then skip the session and output a warning
                except Exception as e:
                    print("Error when fetching the session ID for {}".format(session_title), e)
                    skipping = True
            else:
                skipping = True
            # Check to see if we should continue and download the presentations.
            if skipping == False:
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
                            # File is not a pdf so add to the other files array
                            else:
                                # Change the output folder for syncing to the other files folder on s3
                                output_folder = "other_files/"
                                # Add output folder to output path - prepend the session_id as a unique identifier
                                # All files are stored in the same bucket so if two users upload a file named presentation.pptx
                                # then one would write over the other.
                                output_filename = "{0}-{1}".format(session_id, session_file["name"])
                                # Append the new file to the other files array
                                other_files.append(output_filename)

                            # Download the file
                            downloaded = self.grab_file(session_id, session_file["path"], output_filename, output_folder)

                        if found_pdf == False:
                            try:
                                speakers = session["speakers"]
                            except Exception as e:
                                speakers = None
                            if speakers != None:
                                speakers = self.getDetailedSpeakers(speakers)
                            self.missing_presentations.append(
                                [session_id, speakers])

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
                    self.missing_presentations.append([session_id, speakers])
                    print("No files found for {}".format(session_id))

        print("Please sync the presentations folder using the command below:")
        print("aws s3 --profile connect-linaro-org-Owner cp presentations/ s3://connect.linaro.org/{}/presentations/ --recursive".format(self.connect_code))
        input("Press enter to continue...")

        print("Please sync the other_files dir to s3 with the command below:")
        print("aws s3 --profile connect-linaro-org-Owner cp other_files/ s3://connect.linaro.org/{}/other_files/ --recursive".format(self.connect_code))
        input("Press enter to continue...")

        with open("missing_presentations.txt", "w") as missing_presentations_file:
            for each in self.missing_presentations:
                missing_presentations_file.write(str(each) + "\n")

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

        output =  output_path + output_filename

        # Try to download the image and Except errors and return as false.
        try:
            opener = request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            request.install_opener(opener)
            # Check to see if file doesn't exist locally.
            if not os.path.exists(output):
                download_file = request.urlretrieve(url, output)
                if self._verbose:
                    print("Downloaded {}".format(output_filename), download_file)
            # If file exists
            else:
                # Check headers and get Content-Length
                header_check_request = request.urlopen(url)
                server_size = header_check_request.headers['Content-Length']
                # Get size of local file
                local_size = os.path.getsize(output)
                # Check to see if file size differs and if it does - download the updated file
                print("{0} vs {1}".format(local_size, server_size))
                if int(server_size) != int(local_size):
                    print("File size does not match so downloading new file for {0}".format(session_id))
                    download_file = request.urlretrieve(url, output)
                # If matches file size on server then do nothing but output a warning if verbose
                else:
                    # check difference between two files
                    if self._verbose:
                        print("Skipping download for {0}".format(output_filename))
            return True
        except Exception as e:
            print(e)
            return False

    def updateGooglesheet(self):
        """
        Updates a Googlesheet defined in googlesheet.py with a list of sessions that are
        missing presentations
        """

        self.googlesheet.updateGoogleSheet(self.missing_presentations)

if __name__ == "__main__":

    presentations = SchedPresentationExportTool("https://linaroconnectsandiego.sched.com", "san19")
    presentations.updateGooglesheet()
