import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook
from nbformat import v3, v4
import codecs
from os import linesep, path
import uuid
from . import utils
import re
from typing import List
from .lv_types import VisArgs

class NotebookMaker:
    def __init__(self, watcher, filename:str=None) -> None:
        self.filename = filename or (
            f'{path.splitext(watcher.filename)[0]}.ipynb'
            if watcher.filename
            else 'tensorwatch.ipynb'
        )

        self.cells = []
        self._default_vis_args = VisArgs()

        watcher_args_str = NotebookMaker._get_vis_args(watcher)

        # create initial cell
        self.cells.append(
            new_code_cell(
                source=linesep.join(
                    [
                        '%matplotlib notebook',
                        'import tensorwatch as tw',
                        f'client = tw.WatcherClient({NotebookMaker._get_vis_args(watcher)})',
                    ]
                )
            )
        )

    def _get_vis_args(self) -> str:
        args_strs = []
        for param, default_v in [('port', 0), ('filename', None)]:
            if hasattr(self, param):
                v = getattr(self, param)
                if v==default_v or (v is None and default_v is None):
                    continue
                args_strs.append(f"{param}={NotebookMaker._val2str(v)}")
        return ', '.join(args_strs)

    def _get_stream_identifier(self, event_name, stream_name, stream_index) -> str:
        if stream_name and not utils.is_uuid4(stream_name):
            return f'{self}{stream_index}_{utils.str2identifier(stream_name)[:8]}'
        if event_name is not None and event_name != '':
            return f'{self}_{event_name}_{stream_index}'
        else:
            return self + str(stream_index)

    def _val2str(self) -> str:
        # TODO: shall we raise error if non str, bool, number (or its container) parameters?
        return str(self) if not isinstance(self, str) else f"'{self}'"

    def _add_vis_args_str(self, stream_info, param_strs:List[str]) -> None:
        default_args = self._default_vis_args.__dict__
        if not stream_info.req.vis_args:
            return
        for k, v in stream_info.req.vis_args.__dict__.items():
            if k in default_args:
                default_v = default_args[k]
                if (v is None and default_v is None) or (v==default_v):
                    continue # skip param if its value is not changed from default
                param_strs.append(f"{k}={NotebookMaker._val2str(v)}")

    def _get_stream_code(self, event_name, stream_name, stream_index, stream_info) -> List[str]:
        stream_identifier = f's{str(stream_index)}'
        lines = [f"{stream_identifier} = client.open_stream(name='{stream_name}')"]
        vis_identifier = f'v{str(stream_index)}'
        vis_args_strs = [f'stream={stream_identifier}']
        self._add_vis_args_str(stream_info, vis_args_strs)
        lines.extend(
            (
                f"{vis_identifier} = tw.Visualizer({', '.join(vis_args_strs)})",
                f"{vis_identifier}.show()",
            )
        )
        return lines

    def add_streams(self, event_stream_infos)->None:
        stream_index = 0
        for event_name, stream_infos in event_stream_infos.items(): # per event
            for stream_name, stream_info in stream_infos.items():
                lines = self._get_stream_code(event_name, stream_name, stream_index, stream_info)
                self.cells.append(new_code_cell(source=linesep.join(lines)))
                stream_index += 1

    def write(self):
        nb = new_notebook(cells=self.cells, metadata={'language': 'python',})
        with codecs.open(self.filename, encoding='utf-8', mode='w') as f:
            utils.debug_log('Notebook created', path.realpath(f.name), verbosity=0)
            nbformat.write(nb, f, 4)




