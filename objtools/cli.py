from .boundingbox import BoxFormat
from .annotationset import AnnotationSet
from .evalutation import COCOEvaluator

import argparse
from pathlib import Path


PARSE_CHOICES = {"coco", "yolo", "labelme", "pascalvoc", "openimage", "txt", "cvat"}
PARSE_CHOICES_EXT = {*PARSE_CHOICES, "coco_result"}


def parse_args():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--verbose", "-v", action="store_true")
    # parser.add_argument("--threads", "-j", type=int, default=0)

    subparsers = parser.add_subparsers(dest="mode")
    convert_parser = subparsers.add_parser("convert")
    stats_parser = subparsers.add_parser("summary")
    eval_parser = subparsers.add_parser("evaluate")

    add_convert_args(convert_parser)
    add_stats_args(stats_parser)
    add_eval_args(eval_parser)

    return parser.parse_args()


def add_parse_args(parser: argparse.ArgumentParser, metavar: str = "input", label: str = None):
    parser.add_argument("input", type=Path, metavar=metavar)
    
    group = parser.add_argument_group("Parse options" if label is None else label)
    group.add_argument("--format", "-f", type=str, choices=PARSE_CHOICES, dest="format_in")
    group.add_argument("--img_folder", '-d', type=Path, default=None)
    group.add_argument("--mapping", "-m", type=Path, default=None, dest="mapping_in")
    group.add_argument("--bb_fmt", "-b", type=str, choices=("ltrb", "ltwh", "xywh"), default="ltrb", dest="bb_fmt_in")
    group.add_argument("--norm", "-n", type=str, choices=("abs", "rel"), default="abs", dest="norm_in")
    group.add_argument("--ext", "-e", type=str, default=".txt", dest="ext_in")
    group.add_argument("--img_ext", "-g", type=str, default=".jpg", dest="img_ext_in")
    group.add_argument("--sep", "-p", type=str, default=" ", dest="sep_in")


def add_parse_dets_args(parser: argparse.ArgumentParser):
    parser.add_argument("predictions", type=Path)

    group = parser.add_argument_group("Predictions parse options")
    group.add_argument("--format_dets", "-F", type=str, choices=PARSE_CHOICES_EXT)
    group.add_argument("--img_folder_dets", '-D', type=Path, default=None)
    group.add_argument("--mapping_dets", "-M", type=Path, default=None)
    group.add_argument("--bb_fmt_dets", "-B", type=str, choices=("ltrb", "ltwh", "xywh"), default="ltrb", dest="bb_fmt_dets")
    group.add_argument("--norm_dets", "-N", type=str, choices=("abs", "rel"), default="abs", dest="norm_in_dets")
    group.add_argument("--ext_dets", "-E", type=str, default=".txt")
    group.add_argument("--img_ext_dets", "-G", type=str, default=".jpg")
    group.add_argument("--sep_dets", "-P", type=str, default=" ")


def add_save_args(parser: argparse.ArgumentParser):
    parser.add_argument("output", type=Path)

    group = parser.add_argument_group("Save options")
    group.add_argument("--save_fmt", "-F", type=str, choices=PARSE_CHOICES, dest="format_out")  # TODO: add PARSE_CHOICES_EXT
    group.add_argument("--bb_fmt_out", "-B", type=str, choices=("ltrb", "ltwh", "xywh"), default="ltrb")
    group.add_argument("--norm_out", "-N", type=str, choices=("abs", "rel"), default="abs")
    group.add_argument("--sep_out", "-P", type=str, default=" ")
    group.add_argument("--ext_out", "-E", type=str, default=" ")
    group.add_argument("--coco_auto_ids", "-A", action="store_true")

    mapping_group = group.add_mutually_exclusive_group()
    mapping_group.add_argument("--mapping_out", "-M", type=Path, default=None)
    mapping_group.add_argument("--reverse_mapping_out", "-R", type=Path, default=None)


def add_stats_args(parser: argparse.ArgumentParser):
    add_parse_args(parser)


def add_convert_args(parser: argparse.ArgumentParser): 
    add_parse_args(parser)
    add_save_args(parser)


def add_eval_args(parser: argparse.ArgumentParser):
    add_parse_args(parser, metavar="groundtruths", label="Ground-truths parse options")
    add_parse_dets_args(parser)
    
    parser.add_argument("--save", "-s", type=Path, default=None, dest="save_csv_path")

    # parser.add_argument("--ap", action="append", dest="metrics")
    # parser.add_argument("--ap50", action="append", dest="metrics")
    # parser.add_argument("--iou", type=int, default=None)  # mutually_exclusive_group()
    # etc...


def parse_annotations(args: argparse.Namespace) -> AnnotationSet:
    input: Path = args.input.expanduser().resolve()
    format_in: str = args.format_in

    if format_in == "coco":
        return AnnotationSet.from_coco(input)
    elif format_in == "pascalvoc":
        return AnnotationSet.from_xml(input)
    elif format_in == "openimage":
        assert args.img_folder is not None, "The image directory must be provided for openimage format (required for reading the image size)"
        image_dir: Path = args.img_folder.expanduser().resolve()
        return AnnotationSet.from_openimage(input, image_folder=image_dir)
    elif format_in == "labelme":
        return AnnotationSet.from_labelme(input)
    elif format_in == "cvat":
        return AnnotationSet.from_cvat(input)
    else:
        img_ext: str = args.img_ext_in
        if args.img_folder is not None:
            image_dir: Path = args.img_folder.expanduser().resolve()
        else:
            image_dir = None

        if format_in == "yolo":
            annotations = AnnotationSet.from_yolo(input, image_folder=image_dir, image_extension=img_ext)    
        elif format_in == "txt":
            format_in = BoxFormat.from_string(args.bb_fmt_in)
            relative: bool = args.norm_in == "rel"
            extension: str = args.ext_in
            sep: str = args.sep_in

            annotations = AnnotationSet.from_txt(input, 
                image_folder=image_dir, 
                box_format=format_in, 
                relative=relative,
                file_extension=extension, 
                image_extension=img_ext, 
                separtor=sep)
        else:
            raise ValueError(f"Input format '{format_in}' unknown")

        if args.mapping_in is not None:
            map_path: Path = args.mapping_in.expanduser().resolve()
            mapping = AnnotationSet.parse_names_file(map_path)
            annotations.map_labels(mapping)
        
        return annotations


def parse_dets_annotations(args: argparse.Namespace, coco_gts: AnnotationSet = None) -> AnnotationSet:
    input: Path = args.predictions.expanduser().resolve()
    format_dets: str = args.format_dets

    if format_dets == "coco":
        return AnnotationSet.from_coco(input)
    if format_dets == "coco_result":
        if coco_gts is None:
            raise ValueError("When using 'COCO results', the parsed ground truths must be in 'COCO' format")
        return coco_gts.from_results(input)
    elif format_dets == "pascalvoc":
        return AnnotationSet.from_xml(input)
    elif format_dets == "openimage":
        assert args.image_dir_dets is not None, "The image directory must be provided for openimage format (required for reading the image size)"
        image_dir: Path = args.img_folder_dets.expanduser().resolve()
        return AnnotationSet.from_openimage(input, image_folder=image_dir)
    elif format_dets == "labelme":
        return AnnotationSet.from_labelme(input)
    elif format_dets == "cvat":
        return AnnotationSet.from_cvat(input)
    else:
        img_ext: str = args.img_ext_dets
        if args.image_dir is not None:
            image_dir: Path = args.img_folder_dets.expanduser().resolve()
        else:
            image_dir = None

        if format_dets == "yolo":
            annotations = AnnotationSet.from_yolo(input, image_folder=image_dir, image_extension=img_ext)
        elif format_dets == "txt":
            bb_fmt = BoxFormat.from_string(args.bb_fmt_dets)
            relative: bool = args.norm_dets == "rel"
            extension: str = args.ext_dets
            sep: str = args.sep_dets

            annotations = AnnotationSet.from_txt(input, 
                image_folder=image_dir, 
                box_format=bb_fmt, 
                relative=relative, 
                file_extension=extension,
                image_extension=img_ext,
                separator=sep)
        else:
            raise ValueError(f"Groundtruth format '{format_dets}' unknown")

        if args.mapping_in is not None:
            map_path: Path = args.mapping_in.expanduser().resolve()
            mapping = AnnotationSet.parse_names_file(map_path)
            annotations.map_labels(mapping)

        return annotations


# TODO: Add "coco_result"
def save_annotations(args: argparse.Namespace, annotations: AnnotationSet):
    output: Path = args.output.expanduser().resolve()
    format_out: str = args.format_out

    if args.mapping_out is not None:  # Takes precedence
        map_path: Path = args.mapping_out.expanduser().resolve()
        mapping = AnnotationSet.parse_names_file(map_path)
        annotations.map_labels(mapping)
    elif args.reverse_mapping_out is not None:
        map_path: Path = args.reverse_mapping_out.expanduser().resolve()
        mapping = AnnotationSet.parse_names_file(map_path)
        mapping = {v: k for k, v in mapping.items()}
        annotations.map_labels(mapping)

    if format_out == "coco":
        annotations.save_coco(output, auto_ids=args.coco_auto_ids)
    elif format_out == "pascalvoc":
        annotations.save_xml(output)
    elif format_out == "openimage":
        annotations.save_openimage(output)
    elif format_out == "labelme":
        annotations.save_labelme(output)
    elif format_out == "cvat":
        annotations.save_cvat(output)
    else:
        if format_out == "yolo":
            annotations.save_yolo(output)
        elif format_out == "txt":
            bb_fmt = BoxFormat.from_string(args.bb_fmt_out)
            relative: bool = args.norm_out == "rel"
            extension: str = args.ext_out
            sep: str = args.sep_out

            annotations.save_txt(output, 
                label_to_id=None, 
                box_format=bb_fmt, 
                relative=relative, 
                separator=sep, 
                file_extension=extension)
        else:
            raise ValueError(f"Save format '{format_out}' unknown")


def evaluate(args: argparse.Namespace, groundtruths: AnnotationSet, predictions: AnnotationSet):
    evaluator = COCOEvaluator(groundtruths, predictions)
    evaluator.show_summary()
    
    if args.save_csv_path is not None:
        path = args.save_csv_path.expanduser().resolve()
        evaluator.save_csv(path)


def main():
    args = parse_args()   

    mode = args.mode
    if mode == "convert":
        annotations = parse_annotations(args)
        save_annotations(args, annotations)
    elif mode == "summary":
        annotations = parse_annotations(args)
        annotations.show_stats()
    elif mode == "evaluate":
        groundtruths = parse_annotations(args)
        coco_gts = groundtruths if args.format_dets == "coco_result" else None
        predictions = parse_dets_annotations(args, coco_gts=coco_gts)
        evaluate(args, groundtruths, predictions)
    else:
        raise ValueError(f"Sub-command '{mode}' not recognized.")


if __name__ == "__main__":
    main()