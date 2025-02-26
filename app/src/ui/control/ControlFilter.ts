import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { LocaleController } from "../../controllers/locale";
import "../../features/gif/gifPreset";

@customElement("control-ui-filter")
export class ControlText extends LitElement {
  private lc = new LocaleController(this);

  @property()
  activePanel = "gif";

  createRenderRoot() {
    return this;
  }

  _handleClickChangePanel(name) {
    this.activePanel = name;
    this.requestUpdate();
  }

  render() {
    return html` <div class="row px-2">
      <div class="d-flex col gap-2 overflow-scroll">
        <button
          class="btn btn-sm ${this.activePanel == "gif"
            ? "btn-primary"
            : "btn-default"} text-light mt-1"
          @click=${() => this._handleClickChangePanel("gif")}
        >
          gif
        </button>
        <button
          class="btn btn-sm ${this.activePanel == "transition"
            ? "btn-primary"
            : "btn-default"} text-light mt-1"
          @click=${() => this._handleClickChangePanel("transition")}
        >
          transition
        </button>
        <button
          class="btn btn-sm ${this.activePanel == "overlay"
            ? "btn-primary"
            : "btn-default"} text-light mt-1"
          @click=${() => this._handleClickChangePanel("overlay")}
        >
          overlay
        </button>
        <button
          class="btn btn-sm ${this.activePanel == "audio"
            ? "btn-primary"
            : "btn-default"} text-light mt-1"
          @click=${() => this._handleClickChangePanel("audio")}
        >
          audio
        </button>
      </div>

      <div class="${this.activePanel == "gif" ? "" : "d-none"}">
        <gif-preset></gif-preset>
      </div>
    </div>`;
  }
}
