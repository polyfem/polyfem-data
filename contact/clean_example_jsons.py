import jsbeautifier
import json
import pathlib
import re


class CustomJSONEncoder(json.JSONEncoder):
    """ Hacked JSONEncoder to output pretty float reprs. """
    @staticmethod
    def pretty_float_repr(x):
        return re.sub(r"e(\+?)(\-?)0*", r"e\2", f"{x:g}")

    def iterencode(self, o, _one_shot=False):
        from json.encoder import encode_basestring_ascii, INFINITY, _make_iterencode
        markers = {}
        _encoder = encode_basestring_ascii
        _iterencode = _make_iterencode(
            markers, self.default, _encoder, self.indent,
            CustomJSONEncoder.pretty_float_repr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot)
        return _iterencode(o, 0)


root_path = pathlib.Path(__file__).resolve().parent / "examples"
defaults_path = root_path / "defaults.json"


def diff_dicts(d1, d2):
    diff = {}
    for key in d1.keys():
        if key not in d2:
            diff[key] = d1[key]
        elif isinstance(d1[key], dict) and isinstance(d2[key], dict):
            sub_diff = diff_dicts(d1[key], d2[key])
            if len(sub_diff) != 0:
                diff[key] = sub_diff
        elif d1[key] != d2[key]:
            diff[key] = d1[key]
        # else drop the item by not including it in diff
    return diff


def clean_json(in_path):
    relative_defaults_path = (
        "../" * (len(in_path.relative_to(root_path).parents) - 1)) + "defaults.json"

    with open(in_path) as f:
        params = json.load(f)

    with open(defaults_path) as f:
        default_params = json.load(f)

    if "default_params" in params:
        del params["default_params"]

    reduced_params = {"default_params": relative_defaults_path,
                      **diff_dicts(params, default_params)}

    opts = jsbeautifier.default_options()
    opts.end_with_newline = False
    res = jsbeautifier.beautify(
        json.dumps(reduced_params, cls=CustomJSONEncoder), opts)

    with open(in_path, 'w') as f:
        f.write(res)


def main():
    for path in root_path.glob("**/*.json"):
        if path != defaults_path:
            print(path)
            clean_json(path)


if __name__ == "__main__":
    main()
