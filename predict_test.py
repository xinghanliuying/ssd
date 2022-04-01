import os
import json
import time

import torch
from PIL import Image
import matplotlib.pyplot as plt

import transforms
from src import SSD300, Backbone
from draw_box_utils import draw_box


def create_model(num_classes):
    backbone = Backbone()
    model = SSD300(backbone=backbone, num_classes=num_classes)

    return model


def time_synchronized():
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    return time.time()


def main(predict_data):
    # get devices
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(device)

    # create model
    # 目标检测数 + 背景
    num_classes = 2
    model = create_model(num_classes=num_classes)

    # load train weights
    train_weights = predict_data.model_path
    model.load_state_dict(torch.load(train_weights, map_location=device)['model'])
    model.to(device)

    # read class_indict
    json_path = "./pascal_voc_classes.json"
    assert os.path.exists(json_path), "file '{}' dose not exist.".format(json_path)
    json_file = open(json_path, 'r')
    class_dict = json.load(json_file)
    json_file.close()
    category_index = {v: k for k, v in class_dict.items()}

    # load image
    img_path = predict_data.image_path
    original_img = Image.open(img_path)

    # from pil image to tensor, do not normalize image
    data_transform = transforms.Compose([transforms.Resize(),
                                         transforms.ToTensor(),
                                         transforms.Normalization()])
    img, _ = data_transform(original_img)
    # expand batch dimension
    img = torch.unsqueeze(img, dim=0)

    model.eval()
    with torch.no_grad():
        # initial model
        init_img = torch.zeros((1, 3, 300, 300), device=device)
        model(init_img)

        time_start = time_synchronized()
        predictions = model(img.to(device))[0]  # bboxes_out, labels_out, scores_out
        time_end = time_synchronized()
        print("inference+NMS time: {}".format(time_end - time_start))

        predict_boxes = predictions[0].to("cpu").numpy()
        predict_boxes[:, [0, 2]] = predict_boxes[:, [0, 2]] * original_img.size[0]
        predict_boxes[:, [1, 3]] = predict_boxes[:, [1, 3]] * original_img.size[1]
        predict_classes = predictions[1].to("cpu").numpy()
        predict_scores = predictions[2].to("cpu").numpy()

        if len(predict_boxes) == 0:
            print("没有检测到任何目标!")

        draw_box(original_img,
                 predict_boxes,
                 predict_classes,
                 predict_scores,
                 category_index,
                 thresh=0.5,
                 line_thickness=5)
        plt.imshow(original_img)
        plt.show()
        original_img.save("/kaggle/working/test_result.jpg")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__)

    parser.add_argument('--model-path', default='./', help='model.path')
    # 检测目标类别数(不包含背景)
    parser.add_argument('--image_path', default='./', help='image.path')

    args = parser.parse_args()
    print(args)
    main(args)

