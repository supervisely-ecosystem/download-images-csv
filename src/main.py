import os
import csv

from collections import namedtuple

import supervisely as sly
from dotenv import load_dotenv

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api: sly.Api = sly.Api.from_env()

DatasetData = namedtuple("DatasetData", ["name", "id", "image_infos"])
CSV_HEADER = [
    "Project ID",
    "Project Name",
    "Dataset ID",
    "Dataset Name",
    "Image ID",
    "Image Name",
    "Download URL",
]

SLY_APP_DATA_DIR = sly.app.get_data_dir()
TMP_DIR = os.path.join(SLY_APP_DATA_DIR, "tmp")
RES_DIR = os.path.join(SLY_APP_DATA_DIR, "res")
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)


class ExportImagesCSV(sly.app.Export):
    def process(self, context: sly.app.Export.Context):
        self.selected_project = sly.io.env.project_id(raise_not_found=False)
        self.selected_dataset = sly.io.env.dataset_id(raise_not_found=False)
        self.image_data = []
        self.images_number = 0

        if self.selected_dataset:
            sly.logger.info(f"App launched from dataset: {self.selected_dataset}")

            dataset_info = api.dataset.get_info_by_id(self.selected_dataset)
            project_id = dataset_info.project_id

            self.read_dataset(dataset_info)

        else:
            sly.logger.info(f"App launched from project: {self.selected_project}")
            project_id = self.selected_project

            datasets = api.dataset.get_list(self.selected_project)
            for dataset in datasets:
                dataset_info = api.dataset.get_info_by_id(dataset.id)
                self.read_dataset(dataset_info)

        self.project_name = api.project.get_info_by_id(project_id).name
        self.project_id = project_id
        self.csv_name = self.project_name + ".csv"
        self.csv_path = os.path.join(RES_DIR, self.csv_name)

        self.create_csv()

        return self.csv_path

    def create_csv(self):
        progress = sly.Progress("Creating CSV", self.images_number, need_info_log=True)

        csv_file = open(self.csv_path, "w")
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADER)

        for dataset_data in self.image_data:
            for batched_image_infos in sly.batched(
                dataset_data.image_infos,
            ):
                for image_info in batched_image_infos:
                    # * If image was added to dataset with upload_link() method
                    # * then image_info.link will be not None, otherise full_storage_url will be used.
                    image_url = image_info.link or image_info.full_storage_url

                    print(image_url)

                    writer.writerow(
                        [
                            self.project_id,
                            self.project_name,
                            dataset_data.id,
                            dataset_data.name,
                            image_info.id,
                            image_info.name,
                            image_url,
                        ]
                    )

                    progress.iter_done_report()

        csv_file.close()

    def read_dataset(self, dataset_info):
        image_infos = api.image.get_list(
            dataset_info.id, force_metadata_for_links=False
        )

        self.image_data.append(
            DatasetData(dataset_info.name, dataset_info.id, image_infos)
        )
        self.images_number += len(image_infos)


app = ExportImagesCSV()
app.run()
