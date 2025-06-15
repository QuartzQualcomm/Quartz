import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { LocaleController } from "../../controllers/locale";
@customElement("control-ui-filter")
export class ControlUiFilter extends LitElement {
  private lc = new LocaleController(this);

  @property()
  activePanel = ""; // Default active panel

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
    </div>`;
  }
}
