import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { IUIStore, uiStore } from "./states/uiStore";
import "./features/demo/warningDemoEnv";

@customElement("app-root")
export class App extends LitElement {
  @property()
  uiState: IUIStore = uiStore.getInitialState();

  @property()
  resize = this.uiState.resize;

  @property()
  topBarTitle = this.uiState.topBarTitle;

  createRenderRoot() {
    uiStore.subscribe((state) => {
      this.resize = state.resize;
      this.topBarTitle = state.topBarTitle;
    });

    return this;
  }

  _handleClick() {
    this.uiState.updateVertical(this.resize.vertical.bottom + 2);
  }

  render() {
    return html`
      <asset-upload-drop></asset-upload-drop>
      <tutorial-group>
        <tutorial-popover
          tutorial-idx="1"
          tutorial-title="test"
          tutorial-message="fsdf"
          target-element-id="split_col_1"
        ></tutorial-popover>
      </tutorial-group>

      <div class="top-bar">
        <b>${this.topBarTitle}</b>
      </div>

      <body class="h-100 bg-dark">
        <div id="app"></div>

        <div class="container-fluid" style="height: 97vh;">
          <control-ui
            id="split_top"
            class="row align-items-start"
            style="height: ${this.resize.vertical.top}%;"
          ></control-ui>
          <timeline-ui
            id="split_bottom"
            class="row position-relative split-top align-items-end bg-darker line-top"
            style="height: ${this.resize.vertical.bottom}%;"
          ></timeline-ui>
        </div>

        <offcanvas-list-ui></offcanvas-list-ui>
        <modal-list-ui></modal-list-ui>
        <toast-list-ui></toast-list-ui>

        <div id="menuRightClick"></div>
        <toast-box></toast-box>

        <warning-demo></warning-demo>
      </body>
    `;
  }
}
