import os
import logging
import azure.functions as func
from shutil import copyfile
from ..shared import db_access as DB_Access

# URL to blob storage for testing
DESTINATION_DIRECTORY = "http://akaonboardingstorage.blob.core.windows.net/aka-testimagecontainer"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        url_list = req_body["imageUrls"]
        # url_string = (", ".join(url_list))    # For testing output response
    except ValueError:
        print("Unable to decode JSON body")
        return func.HttpResponse("Unable to decode POST body", status_code=400)

    logging.error(req_body)

    # HttpResponse for testing that JSON URL list was received and parsed correctly
    # return func.HttpResponse(url_string, status_code=200)

    # Build list of image objects to pass to DAL for insertion into DB.
    image_object_list = []
    image_name_list = []

    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]
        image_name_list.append(original_filename)

        # Create ImageInfo object (def in db_access.py)
        # Note: For testing, default image height/width are set to 50x50
        image = DB_Access.ImageInfo(original_filename, url, 50, 50)

        # Append image object to the list
        image_object_list.append(image)

    # Connect to DB
    if(os.getenv("DB_HOST") is None or os.getenv("DB_USER") is None or os.getenv("DB_NAME") is None or os.getenv("DB_PASS") is None):
        return func.HttpResponse("Please set environment variables for DB_HOST, DB_USER, DB_NAME, DB_PASS", status_code=400)
    db = DB_Access.get_connection()

    # Hand off list of image objects to DAL to create rows in database
    # Receive dictionary of mapped { ImageID : ImageURL }
    image_id_url_map = DB_Access.get_image_ids_for_new_images(db, image_object_list)

    # Verify that images were added to database
    added_images = []
    cursor = db.cursor()
    query = ("SELECT imageid, originalimagename FROM image_info WHERE a.originalimagename IN {0}")
    cursor.execute(query.format(image_name_list))
    for row in cursor:
        added_images.append("ImageId: " + str(row[0]) + "\tOriginal Image Name: " + str(row[1]))

    # Construct response string
    response_string = "Images added to database: " + "\n".join(added_images)

    # Copy over images to permanent blob store, get list of URLs to images in permanent storage
    for key, value in image_id_url_map.items():
        file_extension = os.path.splitext(value)[1]
        permanent_storage_directory = DESTINATION_DIRECTORY     # Test directory for now
        permanent_storage_path = permanent_storage_directory + "/" + key + file_extension
        copyfile(value, permanent_storage_path)
    logging.info("Done copying images to permanent blob storage.")

    # Close connection to database.
    db.close()

    # Return list of images that were added to the database for verification
    return func.HttpResponse(response_string, status_code=200)
