import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { LocaleController } from "../../controllers/locale";
import {
  controlPanelStore,
  IControlPanelStore,
} from "../../states/controlPanelStore";

@customElement("control-ui-util")
export class ControlText extends LitElement {
  private lc = new LocaleController(this);

  @property()
  controlPanel: IControlPanelStore = controlPanelStore.getInitialState();

  @property()
  activePanel = this.controlPanel.active;

  createRenderRoot() {
    controlPanelStore.subscribe((state) => {
      this.activePanel = state.active;
    });

    return this;
  }

  _handleClickPanel(name) {
    console.log(name);

    this.controlPanel.updatePanel([...this.activePanel, name]);
  }

  render() {
    return html` <p class="text-light">Utilities</p>
      <div class="row px-2">
        <div
          class="col-4 d-flex flex-column bd-highlight overflow-hidden mt-1 asset"
          @click=${() => this._handleClickPanel("record")}
        >
          <span class="material-symbols-outlined icon-lg align-self-center">
            radio_button_checked
          </span>
          <b class="align-self-center text-light text-center">Record</b>
        </div>

        <div
          class="col-4 d-flex flex-column bd-highlight overflow-hidden mt-1 asset"
          @click=${() => this._handleClickPanel("audioRecord")}
        >
          <span class="material-symbols-outlined icon-lg align-self-center">
            mic
          </span>
          <b class="align-self-center text-light text-center">Audio Record</b>
        </div>

        <div
          class="col-4 d-flex flex-column bd-highlight overflow-hidden mt-1 asset"
          @click=${() => this._handleClickPanel("automaticCaption")}
        >
          <span class="material-symbols-outlined icon-lg align-self-center">
            mic
          </span>
          <b class="align-self-center text-light text-center"
            >Automatic Caption</b
          >
        </div>
      </div>`;
  }
}
