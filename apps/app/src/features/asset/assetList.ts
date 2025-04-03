import { path } from "../../functions/path";
import { LitElement, PropertyValues, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { AssetController } from "../../controllers/asset";
import { LocaleController } from "../../controllers/locale";
import { getLocationEnv } from "../../functions/getLocationEnv";
import { assetContext } from "./context/assetContext";
import { consume } from "@lit/context";

@customElement("asset-list")
export class AssetList extends LitElement {
  blobThumbnail: {};
  nowDirectory: string;
  map: any;
  constructor() {
    super();
    this.blobThumbnail = {};
    this.nowDirectory = "";

    this.map = [];
  }

  @property()
  showType;
  isShowOption = true;

  private lc = new LocaleController(this);

  createRenderRoot() {
    return this;
  }

  render() {
    return html`<div class="row px-2">
      <p
        class="text-light mt-2 text-center ${!this.isShowOption
          ? "d-none"
          : ""} ${getLocationEnv() == "demo" ? "d-none" : ""}"
      >
        ${this.lc.t("setting.need_select_project_folder")}
      </p>
      <p
        class="text-light mt-2 text-center ${!this.isShowOption
          ? "d-none"
          : ""} ${getLocationEnv() != "demo" ? "d-none" : ""}"
      >
        The folder cannot be viewed in the demo version.
      </p>
      <button
        class="btn btn-sm btn-default text-light ${!this.isShowOption
          ? "d-none"
          : ""}"
        onclick="NUGGET.directory.select()"
      >
        ${this.lc.t("setting.select_project_folder")}
      </button>

      ${this.map}
    </div> `;
  }

  getFile(filename) {
    let splitedFilename = filename.split(".");
    let splitedFilenameLength = splitedFilename.length;
    let fileType =
      splitedFilenameLength <= 2
        ? ""
        : splitedFilename[splitedFilenameLength - 1];

    let listBody: HTMLDivElement | null = this.querySelector("div");
    if (listBody == null) return false;
    this.map.push(
      html`<asset-file
        showType="${this.showType}"
        assetName="${filename}"
      ></asset-file>`,
    );
    console.log("AAA", filename);
  }

  getFolder(foldername) {
    let splitedFoldername = foldername.split(".");
    let splitedFoldernameLength = splitedFoldername.length;
    let fileType =
      splitedFoldernameLength <= 2
        ? ""
        : splitedFoldername[splitedFoldernameLength - 1];

    let listBody = this.querySelector("div");
    if (listBody == null) return false;
    this.map.push(
      html`<asset-folder
        showType="${this.showType}"
        assetName="${foldername}"
      ></asset-folder>`,
    );
  }

  clearList() {
    this.map = [];
    this.isShowOption = false;
    this.requestUpdate();
  }
}

@customElement("asset-file")
export class AssetFile extends LitElement {
  directory: any;
  videoBlob: string;
  constructor() {
    super();

    this.classList.add(
      "col-4",
      "d-flex",
      "flex-column",
      "bd-highlight",
      "overflow-hidden",
      "mt-1",
      "asset",
    );

    this.addEventListener("click", this.handleClick.bind(this));

    this.videoBlob = "";

    this.directory = document.querySelector("asset-list").nowDirectory;
  }

  @property()
  assetName;

  @consume({ context: assetContext, subscribe: true })
  @property({ attribute: false })
  public assetOptions = {
    showType: "grid",
  };

  createRenderRoot() {
    return this;
  }

  protected updated(_changedProperties: PropertyValues): void {
    console.log("this.", this.assetOptions.showType);
    if (this.assetOptions.showType == "grid") {
      this.classList.remove("col-12", "flex-row");
      this.classList.add("col-4", "flex-column");
    } else {
      this.classList.remove("col-4", "flex-column");
      this.classList.add("col-12", "flex-row");
    }
  }

  private assetControl = new AssetController();

  render() {
    this.directory = document.querySelector("asset-list").nowDirectory;

    const fileType = NUGGET.mime.lookup(this.assetName).type;

    const nowEnv = getLocationEnv();
    const filepath =
      nowEnv == "electron"
        ? `file://${this.directory}/${this.assetName}`
        : `/api/file?path=${this.directory}/${this.assetName}`;
    const fileUrl = path.encode(filepath);
    const assetList = document.querySelector("asset-list");

    let template;
    if (fileType == "image") {
      template = this.templateImage(fileUrl);
    } else if (fileType == "gif") {
      template = this.templateImage(fileUrl);
    } else if (fileType == "video") {
      if (assetList.blobThumbnail.hasOwnProperty(fileUrl)) {
        let savedThumbnailUrl = assetList.blobThumbnail[fileUrl];
        this.videoBlob = savedThumbnailUrl;
        template = this.templateVideoThumbnail();
      } else {
        let thumbnailUrl = this.captureVideoThumbnail(fileUrl);
        template = this.templateVideoThumbnail();
      }
    } else {
      template = this.template(fileType);
    }

    return template;
  }

  template(filetype = "unknown") {
    const fileIcon = {
      video: "video_file",
      audio: "audio_file",
      unknown: "draft",
    };
    return html`<span
        class="material-symbols-outlined icon-lg align-self-center"
      >
        ${fileIcon[filetype]}
      </span>
      <b class="align-self-center text-ellipsis-scroll text-light text-center"
        >${this.assetName}</b
      >`;
  }

  templateImage(url) {
    this.directory = document.querySelector("asset-list").nowDirectory;

    return html`<img
        src="${url}"
        alt=""
        class="align-self-center asset-preview"
      />
      <b class="align-self-center text-ellipsis-scroll text-light text-center"
        >${this.assetName}</b
      >`;
  }

  templateVideoThumbnail() {
    return html` <div class="position-relative align-self-center">
        <img
          src="${this.videoBlob}"
          alt=""
          class="align-self-center asset-preview w-100"
        />
        <span class="material-symbols-outlined position-absolute icon-center ">
          play_arrow
        </span>
      </div>

      <b class="align-self-center text-ellipsis-scroll text-light text-center"
        >${this.assetName}</b
      >`;
  }

  handleClick() {
    this.directory = document.querySelector("asset-list").nowDirectory;

    this.assetControl.add(`${this.directory}/${this.assetName}`);
    //this.patchToControl(`${this.directory}/${this.filename}`, `${this.directory}`)
  }

  async captureVideoThumbnail(url) {
    const assetList = document.querySelector("asset-list");
    const nowEnv = getLocationEnv();
    const filepath =
      nowEnv == "electron"
        ? `file://${this.directory}/${this.assetName}`
        : `/api/file?path=${this.directory}/${this.assetName}`;
    const fileUrl = path.encode(filepath);

    try {
      const thumbnailUrl = await new Promise((resolve, reject) => {
        fetch(`${url}`)
          .then((res) => {
            return res.blob();
          })
          .then((blob) => {
            const blobUrl = URL.createObjectURL(blob);
            const videoElement = document.createElement("video");

            videoElement.src = blobUrl;
            videoElement.preload = "metadata";

            videoElement.onloadedmetadata = async () => {
              const thumbnailCanvas = document.createElement("canvas");

              videoElement.addEventListener("seeked", () => {
                let width = videoElement.videoWidth;
                let height = videoElement.videoHeight;
                thumbnailCanvas.width = width;
                thumbnailCanvas.height = height;

                let ctx = thumbnailCanvas.getContext("2d");
                if (!ctx) return false;
                ctx.drawImage(
                  videoElement,
                  0,
                  0,
                  thumbnailCanvas.width,
                  thumbnailCanvas.height,
                );

                thumbnailCanvas.toBlob((blob: any) => {
                  try {
                    const newImg = document.createElement("img");
                    const url = URL.createObjectURL(blob);

                    newImg.onload = () => {
                      URL.revokeObjectURL(url);
                    };

                    this.videoBlob = url;
                    this.requestUpdate();
                    assetList.blobThumbnail[fileUrl] = url;
                    resolve(url);
                  } catch (error) {}
                });
              });

              videoElement.currentTime = 1;

              // let image = thumbnailCanvas.toDataURL('image/jpeg');
              // resolve(image)
            };
          });
      });

      return thumbnailUrl;
    } catch (error) {}
  }
}

@customElement("asset-folder")
export class AssetFolder extends LitElement {
  directory: any;

  constructor() {
    super();

    this.classList.add(
      "col-4",
      "d-flex",
      "flex-column",
      "bd-highlight",
      "overflow-hidden",
      "mt-1",
      "asset",
    );

    this.addEventListener("click", this.handleClick.bind(this));

    this.directory = document.querySelector("asset-list").nowDirectory;
  }

  @property()
  assetName;

  createRenderRoot() {
    return this;
  }

  private assetControl = new AssetController();

  render() {
    const template = this.template();
    return template;
  }

  template() {
    return html`<span
        class="material-symbols-outlined icon-lg align-self-center"
      >
        folder
      </span>
      <b class="align-self-center text-ellipsis text-light text-center"
        >${this.assetName}</b
      >`;
  }

  handleClick() {
    this.assetControl.requestAllDir(`${this.directory}/${this.assetName}`);
  }
}
