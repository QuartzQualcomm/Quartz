import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import "./ControlSetting";
import "./ControlText";
import "./ControlExtension";
import "./ControlRender";
import "./ControlUtilities";
import "./ControlFilter";
import "../../features/preview/previewTopBar";
import "../../features/record/screenRecord";
import "../../features/record/audioRecord";
import "../../features/ytdown/ytDownload";

import "../../../../automatic-caption/src/automaticCaption";

import { IUIStore, uiStore } from "../../states/uiStore";
import { TimelineController } from "../../controllers/timeline";
import {
  IControlPanelStore,
  controlPanelStore,
} from "../../states/controlPanelStore";
import { ITimelineStore, useTimelineStore } from "../../states/timelineStore";

@customElement("control-ui")
export class Control extends LitElement {
  @property()
  timelineState: ITimelineStore = useTimelineStore.getInitialState();

  @property()
  timeline: any = this.timelineState.timeline;

  @property()
  uiState: IUIStore = uiStore.getInitialState();

  @property()
  resize = this.uiState.resize;

  @property()
  isAbleResize: boolean = false;

  @property()
  targetResize: "panel" | "preview" = "panel";

  @property()
  controlPanel: IControlPanelStore = controlPanelStore.getInitialState();

  @property()
  activePanel = this.controlPanel.active;

  @property()
  nowActivePanel = this.controlPanel.nowActive;

  createRenderRoot() {
    useTimelineStore.subscribe((state) => {
      this.timeline = state.timeline;
    });

    uiStore.subscribe((state) => {
      this.resize = state.resize;
    });

    controlPanelStore.subscribe((state) => {
      this.activePanel = state.active;
      this.nowActivePanel = state.nowActive;
    });

    window.addEventListener("mouseup", this._handleMouseUp.bind(this));
    window.addEventListener("mousemove", this._handleMouseMove.bind(this));

    return this;
  }

  _handleMouseMove(e) {
    const elementControlComponent = document.querySelector("element-control");

    if (this.isAbleResize) {
      const windowWidth = window.innerWidth - this.resize.chatSidebar;
      const nowX = e.clientX;
      const resizeX = (nowX / windowWidth) * 100;

      if (this.targetResize == "panel" && resizeX <= 20) {
        this.uiState.updateHorizontal(20, this.targetResize);
        elementControlComponent.resizeEvent();
        return false;
      }

      this.uiState.updateHorizontal(resizeX, this.targetResize);
      elementControlComponent.resizeEvent();
    }
  }

  _handleMouseUp() {
    this.isAbleResize = false;
  }

  _handleClickResizePanel() {
    this.targetResize = "panel";
    this.isAbleResize = true;
  }

  _handleClickResizePreview() {
    this.targetResize = "preview";
    this.isAbleResize = true;
  }

  _handleComplateAutoCaption(e) {
    const result = e.detail.result;
    const control = document.querySelector("element-control");

    for (let index = 0; index < result.length; index++) {
      const element = result[index];
      control.addText(element);
    }
  }

  _handleChangeCursorType(e) {
    const type = e.detail.type;

    this.timelineState.setCursorType(type);
  }

  render() {
    return html`
      <div
        id="split_col_1"
        class="bg-darker h-100 overflow-y-hidden overflow-x-hidden position-relative p-0"
        style="width: ${this.resize.horizontal.panel}%;"
      >
        <div
          class="split-col-bar"
          @mousedown=${this._handleClickResizePanel}
        ></div>

        <div
          class=" h-100 w-100 overflow-y-hidden overflow-x-hidden position-absolute "
        >
          <div class="d-flex align-items-start h-100">
            <div
              id="sidebar"
              class="nav sidebar-nav flex-column nav-pills bg-dark h-100 pt-1"
              style="width: 2.5rem;"
              role="tablist"
              aria-orientation="vertical"
            >
              <button
                class="btn-nav active"
                data-bs-toggle="pill"
                data-bs-target="#nav-home"
                type="button"
                role="tab"
                aria-selected="true"
              >
                <span class="material-symbols-outlined"> settings</span>
              </button>

              <button
                class="btn-nav"
                data-bs-toggle="pill"
                data-bs-target="#nav-draft"
                type="button"
                role="tab"
                aria-selected="false"
              >
                <span class="material-symbols-outlined"> draft</span>
              </button>

              <button
                class="btn-nav"
                data-bs-toggle="pill"
                data-bs-target="#nav-text"
                type="button"
                role="tab"
                aria-selected="false"
              >
                <span class="material-symbols-outlined"> text_fields</span>
              </button>


              <button
                class="btn-nav"
                data-bs-toggle="pill"
                data-bs-target="#nav-util"
                type="button"
                role="tab"
                aria-selected="false"
              >
                <span class="material-symbols-outlined"> page_info</span>
              </button>          

              <button
                class="btn-nav"
                data-bs-toggle="pill"
                data-bs-target="#nav-output"
                type="button"
                role="tab"
                aria-selected="false"
              >
                <span class="material-symbols-outlined"> output</span>
              </button>
            </div>
            <div
              class="tab-content overflow-y-scroll overflow-x-hidden  p-2 h-100"
              style="width: calc(100% - 2.5rem);"
            >
              <div
                class="tab-pane fade show active"
                id="nav-home"
                role="tabpanel"
              >
                <control-ui-setting />
              </div>

              <div class="tab-pane fade" id="nav-draft" role="tabpanel">
                <asset-browser></asset-browser>
              </div>

              <div class="tab-pane fade" id="nav-text" role="tabpanel">
                <control-ui-text />
              </div>

              <div class="tab-pane fade" id="nav-option" role="tabpanel">
                <control-ui-extension />
              </div>

              <div class="tab-pane fade" id="nav-util" role="tabpanel">
                <control-ui-util />
              </div>

              <div class="tab-pane fade" id="nav-filter" role="tabpanel">
                <control-ui-filter />
              </div>

              <div class="tab-pane fade" id="nav-output" role="tabpanel">
                <control-ui-render />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- PREVIEW -->
      <div
        id="split_col_2"
        class="h-100 overflow-y-hidden overflow-x-hidden position-relative p-0"
        style="width: ${this.resize.horizontal.preview}%;"
      >
        <div
          class="split-col-bar"
          @mousedown=${this._handleClickResizePreview}
        ></div>

        <preview-top-bar></preview-top-bar>

        <div
          style="height: calc(100% - 2rem);"
          class="position-relative d-flex align-items-center justify-content-center ${this
            .nowActivePanel == ""
            ? ""
            : "d-none"}"
        >
          <div id="videobox">
            <div class="d-flex justify-content-center">
              <div id="video" class="video">
                <preview-canvas></preview-canvas>
                <element-control></element-control>
                <drag-alignment-guide></drag-alignment-guide>
              </div>
            </div>
          </div>
        </div>

        <div
          style="height: calc(100% - 2rem);"
          class="position-relative d-flex align-items-center justify-content-center ${this
            .nowActivePanel == "record"
            ? ""
            : "d-none"}"
        >
          <screen-record-panel></screen-record-panel>
        </div>

        <div
          style="height: calc(100% - 2rem);"
          class="position-relative d-flex align-items-center justify-content-center ${this
            .nowActivePanel == "audioRecord"
            ? ""
            : "d-none"}"
        >
          <audio-record-panel></audio-record-panel>
        </div>

        <div
          style="height: calc(100% - 2rem);"
          class="position-relative d-flex align-items-center justify-content-center ${this
            .nowActivePanel == "ytDownload"
            ? ""
            : "d-none"}"
        >
          <youtube-download></youtube-download>
        </div>

        <div
          style="height: calc(100% - 2rem);"
          class="position-relative d-flex align-items-center justify-content-center ${this
            .nowActivePanel == "automaticCaption"
            ? ""
            : "d-none"}"
        >
          <automatic-caption
            .timeline=${this.timeline}
            .isDev=${false}
            @editComplate=${this._handleComplateAutoCaption}
            @changeCursorType=${this._handleChangeCursorType}
          ></automatic-caption>
        </div>
      </div>

      <!-- OPTION-->
      <div
        id="split_col_3"
        class="bg-darker h-100 overflow-y-scroll overflow-x-hidden position-relative option-window p-2"
        style="width: ${this.resize.horizontal.option}%;"
      >
        <input
          type="hidden"
          id="optionTargetElement"
          value="aaaa-aaaa-aaaa-aaaa"
        />

        <option-group>
          <option-text></option-text>
          <option-image></option-image>
          <option-video></option-video>
          <option-audio></option-audio>
          <option-shape></option-shape>
        </option-group>
      </div>
    `;
  }
}
