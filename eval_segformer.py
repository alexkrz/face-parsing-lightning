from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from src.datamodule import SegmentationDataset
from src.pl_module import SegformerConfig, SegformerForSemanticSegmentation


def main(
    img_dir: str = "data/025_08.jpg",
    log_dir: str = "logs_pl/segformer/version_0",
    ckpt_fp: str = "checkpoints/epoch=1-step=6750.ckpt",
):
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print("device:", device)

    pil_img = Image.open(img_dir)
    print(pil_img)
    img_transforms = SegmentationDataset.segformer_img_tfms

    img_in = img_transforms(pil_img)
    img_in = img_in.unsqueeze(0)  # Add batch dimension
    print(img_in.shape)

    # Load model from checkpoint
    log_dir = Path(log_dir)  # type: Path
    config = SegformerConfig.from_json_file(log_dir / "model_config.json")
    model = SegformerForSemanticSegmentation(config)

    ckpt = torch.load(log_dir / ckpt_fp, weights_only=True)
    # print([key for key in ckpt["state_dict"].keys() if "decode_head" in key])

    # Remove "model." prefix from checkpoint keys
    state_dict = {key.replace("model.", ""): value for key, value in ckpt["state_dict"].items()}

    # print(model.state_dict().keys())
    msg = model.load_state_dict(state_dict)
    print(msg)

    # Run inference
    model.eval()
    img_in = img_in.to(device)
    model.to(device)
    outs = model.forward(pixel_values=img_in, labels=None)
    logits = outs.logits  # shape (batch_size, num_labels, ~height/4, ~width/4)
    print(logits.shape)

    # Adjust logits
    # resize output to match input image dimensions
    upsampled_logits = torch.nn.functional.interpolate(
        logits,
        size=pil_img.size,
        mode="bilinear",
        align_corners=False,  # H x W
    )

    # get label masks
    labels = upsampled_logits.argmax(dim=1)[0]

    # move to CPU to visualize in matplotlib
    labels_viz = labels.cpu().numpy()
    print(labels_viz.shape)


if __name__ == "__main__":
    main()
