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
        "rect": [ 249.0, 205.0, 1077.0, 941.0 ],
        "openinpresentation": 1,
        "boxes": [
            {
                "box": {
                    "fontface": 1,
                    "fontsize": 14.0,
                    "id": "obj-title",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 20.0, 10.0, 300.0, 22.0 ],
                    "text": "Chorus using Faust dual_tap_delay~"
                }
            },
            {
                "box": {
                    "id": "obj-subtitle",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 20.0, 32.0, 400.0, 20.0 ],
                    "text": "9th-order Lagrange interpolation, signal-rate delay modulation"
                }
            },
            {
                "box": {
                    "comment": "Audio Input",
                    "id": "obj-inlet",
                    "index": 0,
                    "maxclass": "inlet",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 369.0, 218.0, 30.0, 30.0 ]
                }
            },
            {
                "box": {
                    "comment": "Audio Output",
                    "id": "obj-outlet",
                    "index": 0,
                    "maxclass": "outlet",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 290.0, 812.0, 30.0, 30.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-label-delay",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 70.0, 50.0, 20.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 10.0, 10.0, 50.0, 20.0 ],
                    "text": "Delay",
                    "textjustification": 1
                }
            },
            {
                "box": {
                    "id": "obj-label-rate",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 90.0, 70.0, 50.0, 20.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 65.0, 10.0, 50.0, 20.0 ],
                    "text": "Rate",
                    "textjustification": 1
                }
            },
            {
                "box": {
                    "id": "obj-label-depth",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 150.0, 70.0, 50.0, 20.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 120.0, 10.0, 50.0, 20.0 ],
                    "text": "Depth",
                    "textjustification": 1
                }
            },
            {
                "box": {
                    "id": "obj-label-wet",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 210.0, 70.0, 50.0, 20.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 175.0, 10.0, 50.0, 20.0 ],
                    "text": "Wet",
                    "textjustification": 1
                }
            },
            {
                "box": {
                    "id": "obj-label-xover",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 270.0, 70.0, 50.0, 20.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 230.0, 10.0, 50.0, 20.0 ],
                    "text": "Xover",
                    "textjustification": 1
                }
            },
            {
                "box": {
                    "id": "obj-slider-delay",
                    "maxclass": "slider",
                    "min": 5.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 40.0, 95.0, 20.0, 140.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 20.0, 35.0, 20.0, 140.0 ],
                    "size": 45.0,
                    "varname": "Delay"
                }
            },
            {
                "box": {
                    "id": "obj-slider-rate",
                    "maxclass": "slider",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 100.0, 95.0, 20.0, 140.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 75.0, 35.0, 20.0, 140.0 ],
                    "size": 20.0,
                    "varname": "Rate"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "obj-slider-depth",
                    "maxclass": "slider",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 160.0, 95.0, 20.0, 140.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 130.0, 35.0, 20.0, 140.0 ],
                    "size": 10.0
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "obj-slider-wet",
                    "maxclass": "slider",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 220.0, 95.0, 20.0, 140.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 185.0, 35.0, 20.0, 140.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "obj-slider-xover",
                    "maxclass": "slider",
                    "min": 20.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 280.0, 95.0, 20.0, 140.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 240.0, 35.0, 20.0, 140.0 ],
                    "size": 480.0
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-num-delay",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 245.0, 45.0, 22.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 10.0, 185.0, 45.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-num-rate",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 90.0, 245.0, 45.0, 22.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 65.0, 185.0, 45.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-num-depth",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 150.0, 245.0, 45.0, 22.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 120.0, 185.0, 45.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-num-wet",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 210.0, 245.0, 45.0, 22.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 175.0, 185.0, 45.0, 22.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "obj-num-xover",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 270.0, 245.0, 45.0, 22.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 230.0, 185.0, 45.0, 22.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-svf",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 4,
                    "outlettype": [ "signal", "signal", "signal", "signal" ],
                    "patching_rect": [ 369.0, 331.0, 100.0, 22.0 ],
                    "text": "svf~ 300 0.707"
                }
            },
            {
                "box": {
                    "id": "obj-rand",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 100.0, 300.0, 45.0, 22.0 ],
                    "text": "rand~"
                }
            },
            {
                "box": {
                    "id": "obj-sig-delay",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 40.0, 300.0, 36.0, 22.0 ],
                    "text": "sig~"
                }
            },
            {
                "box": {
                    "id": "obj-sig-depth",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 160.0, 300.0, 36.0, 22.0 ],
                    "text": "sig~"
                }
            },
            {
                "box": {
                    "id": "obj-mult-depth",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 100.0, 340.0, 79.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "obj-add-delay1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 40.0, 446.0, 79.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-neg",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 166.0, 386.0, 40.0, 22.0 ],
                    "text": "*~ -1"
                }
            },
            {
                "box": {
                    "id": "obj-add-delay2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 139.0, 434.0, 46.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-dual-tap",
                    "maxclass": "newobj",
                    "numinlets": 3,
                    "numoutlets": 2,
                    "outlettype": [ "signal", "signal" ],
                    "patching_rect": [ 340.0, 578.0, 200.0, 22.0 ],
                    "text": "dual_tap_delay~"
                }
            },
            {
                "box": {
                    "id": "obj-add-taps",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 340.0, 625.0, 40.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-scale-taps",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 340.0, 655.0, 50.0, 22.0 ],
                    "text": "*~ 0.5"
                }
            },
            {
                "box": {
                    "id": "obj-mult-wet",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 340.0, 709.0, 29.5, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "obj-sig-wet",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 210.0, 645.0, 36.0, 22.0 ],
                    "text": "sig~"
                }
            },
            {
                "box": {
                    "id": "obj-oneminus",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "float" ],
                    "patching_rect": [ 437.0, 398.0, 50.0, 22.0 ],
                    "text": "!- 1."
                }
            },
            {
                "box": {
                    "id": "obj-sig-dry",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 451.0, 439.0, 36.0, 22.0 ],
                    "text": "sig~"
                }
            },
            {
                "box": {
                    "id": "obj-mult-dry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 411.0, 686.0, 59.0, 22.0 ],
                    "text": "*~"
                }
            },
            {
                "box": {
                    "id": "obj-add-wetdry",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 340.0, 739.0, 89.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-add-bands",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "signal" ],
                    "patching_rect": [ 290.0, 769.0, 69.0, 22.0 ],
                    "text": "+~"
                }
            },
            {
                "box": {
                    "id": "obj-panel",
                    "maxclass": "panel",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 55.0, 310.0, 225.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 0.0, 0.0, 290.0, 220.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-pattr-delay",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 500.0, 130.0, 208.0, 22.0 ],
                    "saved_object_attributes": {
                        "initial": [ 20 ],
                        "parameter_enable": 0,
                        "parameter_mappable": 0
                    },
                    "text": "pattr Delay @bindto Delay @initial 20",
                    "varname": "Delay[1]"
                }
            },
            {
                "box": {
                    "id": "obj-pattr-rate",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 500.0, 160.0, 150.0, 22.0 ],
                    "restore": [ 5 ],
                    "saved_object_attributes": {
                        "parameter_enable": 0,
                        "parameter_mappable": 0
                    },
                    "text": "pattr Rate @bindto Rate",
                    "varname": "Rate[1]"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-outlet", 0 ],
                    "source": [ "obj-add-bands", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-dual-tap", 1 ],
                    "midpoints": [ 49.5, 498.5625, 440.0, 498.5625 ],
                    "source": [ "obj-add-delay1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-dual-tap", 2 ],
                    "midpoints": [ 148.5, 478.38671875, 530.5, 478.38671875 ],
                    "source": [ "obj-add-delay2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-scale-taps", 0 ],
                    "source": [ "obj-add-taps", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-bands", 1 ],
                    "source": [ "obj-add-wetdry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-taps", 1 ],
                    "source": [ "obj-dual-tap", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-taps", 0 ],
                    "source": [ "obj-dual-tap", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-svf", 0 ],
                    "source": [ "obj-inlet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-delay1", 1 ],
                    "order": 1,
                    "source": [ "obj-mult-depth", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-neg", 0 ],
                    "order": 0,
                    "source": [ "obj-mult-depth", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-wetdry", 1 ],
                    "source": [ "obj-mult-dry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-wetdry", 0 ],
                    "source": [ "obj-mult-wet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-delay2", 1 ],
                    "source": [ "obj-neg", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-delay2", 0 ],
                    "midpoints": [ 39.5, 275.0, 15.0, 275.0, 15.0, 415.11328125, 148.5, 415.11328125 ],
                    "order": 0,
                    "source": [ "obj-num-delay", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-sig-delay", 0 ],
                    "midpoints": [ 39.5, 275.0, 49.5, 275.0 ],
                    "order": 1,
                    "source": [ "obj-num-delay", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-sig-depth", 0 ],
                    "source": [ "obj-num-depth", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-rand", 0 ],
                    "source": [ "obj-num-rate", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-oneminus", 0 ],
                    "midpoints": [ 219.5, 395.24609375, 446.5, 395.24609375 ],
                    "order": 0,
                    "source": [ "obj-num-wet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-sig-wet", 0 ],
                    "order": 1,
                    "source": [ "obj-num-wet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-svf", 1 ],
                    "midpoints": [ 279.5, 308.26953125, 330.0, 308.26953125, 330.0, 308.703125, 419.0, 308.703125 ],
                    "source": [ "obj-num-xover", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-sig-dry", 0 ],
                    "source": [ "obj-oneminus", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-depth", 0 ],
                    "source": [ "obj-rand", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-wet", 0 ],
                    "source": [ "obj-scale-taps", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-delay1", 0 ],
                    "source": [ "obj-sig-delay", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-depth", 1 ],
                    "source": [ "obj-sig-depth", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-dry", 1 ],
                    "source": [ "obj-sig-dry", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-wet", 1 ],
                    "source": [ "obj-sig-wet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-num-delay", 0 ],
                    "source": [ "obj-slider-delay", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-num-depth", 0 ],
                    "source": [ "obj-slider-depth", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-num-rate", 0 ],
                    "source": [ "obj-slider-rate", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-num-wet", 0 ],
                    "source": [ "obj-slider-wet", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-num-xover", 0 ],
                    "source": [ "obj-slider-xover", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-add-bands", 0 ],
                    "midpoints": [ 378.5, 376.3515625, 280.0, 376.3515625, 280.0, 580.0, 299.5, 580.0 ],
                    "source": [ "obj-svf", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-dual-tap", 0 ],
                    "midpoints": [ 405.5, 437.1015625, 349.5, 437.1015625 ],
                    "order": 1,
                    "source": [ "obj-svf", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-mult-dry", 0 ],
                    "midpoints": [ 405.5, 374.46875, 517.49609375, 374.46875, 517.49609375, 520.0, 420.5, 520.0 ],
                    "order": 0,
                    "source": [ "obj-svf", 1 ]
                }
            }
        ],
        "autosave": 0
    }
}