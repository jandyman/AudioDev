{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 1,
            "revision": 1,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 100.0, 100.0, 900.0, 700.0 ],
        "openinpresentation": 1,
        "boxes": [
            {
                "box": {
                    "id": "obj-title",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 15.0, 500.0, 22.0 ],
                    "text": "Attack Detector File Test",
                    "fontsize": 14.0,
                    "fontface": 1,
                    "presentation": 1,
                    "presentation_rect": [ 15.0, 10.0, 300.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-instructions",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 40.0, 500.0, 22.0 ],
                    "text": "1. Audio on  2. Click 'read' to load wav  3. Click 'process'",
                    "presentation": 1,
                    "presentation_rect": [ 15.0, 35.0, 400.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-ezdac",
                    "maxclass": "ezdac~",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "patching_rect": [ 700.0, 15.0, 45.0, 45.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 350.0, 10.0, 45.0, 45.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-read",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 50.0, 80.0, 40.0, 22.0 ],
                    "text": "read",
                    "presentation": 1,
                    "presentation_rect": [ 15.0, 70.0, 40.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-buf-input",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 50.0, 115.0, 150.0, 22.0 ],
                    "text": "buffer~ input 10000"
                }
            },
            {
                "box": {
                    "id": "obj-loaded",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 210.0, 115.0, 100.0, 22.0 ],
                    "text": "print file_loaded"
                }
            },
            {
                "box": {
                    "id": "obj-process",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 50.0, 170.0, 55.0, 22.0 ],
                    "text": "process",
                    "presentation": 1,
                    "presentation_rect": [ 15.0, 100.0, 55.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-sel-process",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 50.0, 200.0, 100.0, 22.0 ],
                    "text": "sel process"
                }
            },
            {
                "box": {
                    "id": "obj-start-seq",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "bang", "int", "int" ],
                    "patching_rect": [ 50.0, 235.0, 250.0, 22.0 ],
                    "text": "t b 1 1"
                }
            },
            {
                "box": {
                    "id": "obj-send-rec",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 220.0, 270.0, 90.0, 22.0 ],
                    "text": "s rec-enable"
                }
            },
            {
                "box": {
                    "id": "obj-send-play",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 135.0, 270.0, 80.0, 22.0 ],
                    "text": "s play-toggle"
                }
            },
            {
                "box": {
                    "id": "obj-play",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "bang" ],
                    "patching_rect": [ 50.0, 330.0, 120.0, 22.0 ],
                    "text": "play~ input"
                }
            },
            {
                "box": {
                    "id": "obj-recv-play",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 180.0, 300.0, 80.0, 22.0 ],
                    "text": "r play-toggle"
                }
            },
            {
                "box": {
                    "id": "obj-attack-det",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "signal", "signal", "signal", "signal", "signal" ],
                    "patching_rect": [ 50.0, 380.0, 550.0, 22.0 ],
                    "text": "attack_detector~"
                }
            },
            {
                "box": {
                    "id": "obj-recv-rec",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 650.0, 380.0, 90.0, 22.0 ],
                    "text": "r rec-enable"
                }
            },
            {
                "box": {
                    "id": "obj-rec1",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 50.0, 430.0, 170.0, 22.0 ],
                    "text": "record~ out_trigger"
                }
            },
            {
                "box": {
                    "id": "obj-rec2",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 180.0, 430.0, 180.0, 22.0 ],
                    "text": "record~ out_threshold"
                }
            },
            {
                "box": {
                    "id": "obj-rec3",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 310.0, 430.0, 180.0, 22.0 ],
                    "text": "record~ out_fast_env"
                }
            },
            {
                "box": {
                    "id": "obj-rec4",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 440.0, 430.0, 180.0, 22.0 ],
                    "text": "record~ out_slow_env"
                }
            },
            {
                "box": {
                    "id": "obj-rec5",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 570.0, 430.0, 190.0, 22.0 ],
                    "text": "record~ out_note_ended"
                }
            },
            {
                "box": {
                    "id": "obj-buf1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 50.0, 470.0, 200.0, 22.0 ],
                    "text": "buffer~ out_trigger 10000"
                }
            },
            {
                "box": {
                    "id": "obj-buf2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 180.0, 470.0, 210.0, 22.0 ],
                    "text": "buffer~ out_threshold 10000"
                }
            },
            {
                "box": {
                    "id": "obj-buf3",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 310.0, 470.0, 210.0, 22.0 ],
                    "text": "buffer~ out_fast_env 10000"
                }
            },
            {
                "box": {
                    "id": "obj-buf4",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 440.0, 470.0, 210.0, 22.0 ],
                    "text": "buffer~ out_slow_env 10000"
                }
            },
            {
                "box": {
                    "id": "obj-buf5",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "float", "bang" ],
                    "patching_rect": [ 570.0, 470.0, 220.0, 22.0 ],
                    "text": "buffer~ out_note_ended 10000"
                }
            },
            {
                "box": {
                    "id": "obj-done-delay",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 150.0, 330.0, 70.0, 22.0 ],
                    "text": "delay 100"
                }
            },
            {
                "box": {
                    "id": "obj-stop-seq",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 4,
                    "outlettype": [ "bang", "int", "int", "bang" ],
                    "patching_rect": [ 150.0, 365.0, 250.0, 22.0 ],
                    "text": "t b 0 0 b"
                }
            },
            {
                "box": {
                    "id": "obj-stop-play",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 230.0, 400.0, 80.0, 22.0 ],
                    "text": "s play-toggle"
                }
            },
            {
                "box": {
                    "id": "obj-stop-rec",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 310.0, 400.0, 90.0, 22.0 ],
                    "text": "s rec-enable"
                }
            },
            {
                "box": {
                    "id": "obj-write1",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 50.0, 530.0, 260.0, 22.0 ],
                    "text": "writewave /Users/andy/Dropbox/Developer/AudioDev/test_audio_out/attack_det_trigger.wav"
                }
            },
            {
                "box": {
                    "id": "obj-write2",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 180.0, 530.0, 280.0, 22.0 ],
                    "text": "writewave /Users/andy/Dropbox/Developer/AudioDev/test_audio_out/attack_det_threshold.wav"
                }
            },
            {
                "box": {
                    "id": "obj-write3",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 310.0, 530.0, 270.0, 22.0 ],
                    "text": "writewave /Users/andy/Dropbox/Developer/AudioDev/test_audio_out/attack_det_fast_env.wav"
                }
            },
            {
                "box": {
                    "id": "obj-write4",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 440.0, 530.0, 270.0, 22.0 ],
                    "text": "writewave /Users/andy/Dropbox/Developer/AudioDev/test_audio_out/attack_det_slow_env.wav"
                }
            },
            {
                "box": {
                    "id": "obj-write5",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 570.0, 530.0, 280.0, 22.0 ],
                    "text": "writewave /Users/andy/Dropbox/Developer/AudioDev/test_audio_out/attack_det_note_ended.wav"
                }
            },
            {
                "box": {
                    "id": "obj-save-trig",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "bang", "bang", "bang", "bang", "bang" ],
                    "patching_rect": [ 50.0, 560.0, 550.0, 22.0 ],
                    "text": "t b b b b b"
                }
            },
            {
                "box": {
                    "id": "obj-print-done",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 50.0, 600.0, 200.0, 22.0 ],
                    "text": "print DONE_saving_outputs"
                }
            },
            {
                "box": {
                    "id": "obj-output-info",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 50.0, 630.0, 500.0, 22.0 ],
                    "text": "Saves to test_audio_out/: attack_det_trigger.wav, _threshold, _fast_env, _slow_env, _note_ended",
                    "presentation": 1,
                    "presentation_rect": [ 15.0, 135.0, 500.0, 22.0 ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-buf-input", 0 ],
                    "source": [ "obj-read", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-loaded", 0 ],
                    "source": [ "obj-buf-input", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-sel-process", 0 ],
                    "source": [ "obj-process", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-start-seq", 0 ],
                    "source": [ "obj-sel-process", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-play", 0 ],
                    "source": [ "obj-start-seq", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-send-play", 0 ],
                    "source": [ "obj-start-seq", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-send-rec", 0 ],
                    "source": [ "obj-start-seq", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-play", 0 ],
                    "source": [ "obj-recv-play", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-attack-det", 0 ],
                    "source": [ "obj-play", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-done-delay", 0 ],
                    "source": [ "obj-play", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-stop-seq", 0 ],
                    "source": [ "obj-done-delay", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-stop-play", 0 ],
                    "source": [ "obj-stop-seq", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-stop-rec", 0 ],
                    "source": [ "obj-stop-seq", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-save-trig", 0 ],
                    "source": [ "obj-stop-seq", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec1", 0 ],
                    "source": [ "obj-attack-det", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec2", 0 ],
                    "source": [ "obj-attack-det", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec3", 0 ],
                    "source": [ "obj-attack-det", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec4", 0 ],
                    "source": [ "obj-attack-det", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec5", 0 ],
                    "source": [ "obj-attack-det", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec1", 0 ],
                    "source": [ "obj-recv-rec", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec2", 0 ],
                    "source": [ "obj-recv-rec", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec3", 0 ],
                    "source": [ "obj-recv-rec", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec4", 0 ],
                    "source": [ "obj-recv-rec", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rec5", 0 ],
                    "source": [ "obj-recv-rec", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-write1", 0 ],
                    "source": [ "obj-save-trig", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-write2", 0 ],
                    "source": [ "obj-save-trig", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-write3", 0 ],
                    "source": [ "obj-save-trig", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-write4", 0 ],
                    "source": [ "obj-save-trig", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-write5", 0 ],
                    "source": [ "obj-save-trig", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-buf1", 0 ],
                    "source": [ "obj-write1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-buf2", 0 ],
                    "source": [ "obj-write2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-buf3", 0 ],
                    "source": [ "obj-write3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-buf4", 0 ],
                    "source": [ "obj-write4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-buf5", 0 ],
                    "source": [ "obj-write5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-print-done", 0 ],
                    "source": [ "obj-save-trig", 0 ]
                }
            }
        ],
        "autosave": 0
    }
}
