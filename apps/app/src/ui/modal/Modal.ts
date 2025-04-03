import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { LocaleController } from "../../controllers/locale";

@customElement("modal-list-ui")
export class ModalList extends LitElement {
  private lc = new LocaleController(this);

  createRenderRoot() {
    return this;
  }

  openRenderedVideoFolder() {
    const projectFolder = document.querySelector("#projectFolder").value;
    window.electronAPI.req.filesystem.openDirectory(projectFolder);
  }

  forceClose() {
    //ipcRenderer.send('FORCE_CLOSE')
    window.electronAPI.req.app.forceClose();
  }

  _handleClickChangeLang(lang) {
    this.lc.changeLanguage(lang);
    const needsToRestartModal = new bootstrap.Modal("#NeedsToRestart", {
      keyboard: false,
    });
    needsToRestartModal.show();
  }

  _handleClickRestart() {
    window.electronAPI.req.app.restart();
  }

  render() {
    return html`
      <dds-modal
        modal-id="exportVideoModal"
        modal-title="영상 내보내기"
        modal-subtitle=""
      >
        <dds-content>
          <div class="mb-3">
            <video id="exportVideo" controls?="controls"></video>
          </div>
        </dds-content>
        <dds-modal-button
          button-color="btn-blue"
          button-text-color="text-primary"
          is-dismiss="false"
          >저장</dds-modal-button
        >
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >취소</dds-modal-button
        >
      </dds-modal>

      <dds-modal modal-id="progressRender" modal-title="Rendering...">
        <dds-content>
          <div class="mb-3">
            <div class="progress">
              <div
                id="progress"
                class="progress-bar"
                role="progressbar"
                style="width: 25%;"
                aria-valuenow="25"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                25%
              </div>
            </div>
            <b class="text-secondary"
              ><i class="fas fa-info-circle"></i>
              <span id="remainingTime">-s left</span>
            </b>

            <!-- <b class="text-secondary"
              ><i class="fas fa-info-circle"></i> 랜더링 100%에 도달해도
              일정시간 지연될 수 있어요.
            </b> -->
          </div>
        </dds-content>
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >Close</dds-modal-button
        >
      </dds-modal>

      <dds-modal modal-id="downloadFfmpeg" modal-title="FFMPEG 다운로드중">
        <dds-content>
          <div class="mb-3">
            <div class="progress">
              <div
                id="download_progress_ffmpeg"
                class="progress-bar"
                role="progressbar"
                style="width: 25%;"
                aria-valuenow="25"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                25%
              </div>
            </div>
          </div>
        </dds-content>
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >Close</dds-modal-button
        >
      </dds-modal>

      <dds-modal modal-id="progressFinish" modal-title="Rendering is complete">
        <dds-content>
          <div class="mb-3"></div>
        </dds-content>
        <dds-modal-button
          button-color="btn-blue-fill"
          is-dismiss="false"
          @click=${this.openRenderedVideoFolder}
          >Open Saved Folder</dds-modal-button
        >
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >Close</dds-modal-button
        >
      </dds-modal>

      <dds-modal
        modal-id="progressError"
        modal-title="랜더링중 문제가 발생했어요"
      >
        <dds-content>
          <div class="mb-3">
            <p id="progressErrorMsg" class="text-secondary"></p>
          </div>
        </dds-content>
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >닫기</dds-modal-button
        >
      </dds-modal>

      <dds-modal
        modal-id="whenClose"
        modal-title="Are you sure you want to exit the program?"
        modal-subtitle="Changes will not be saved."
      >
        <dds-content>
          <div class="mb-3"></div>
        </dds-content>
        <dds-modal-button
          button-color="btn-red-fill"
          is-dismiss="false"
          @click=${this.forceClose}
          >Yes, I'll exit.</dds-modal-button
        >
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >No</dds-modal-button
        >
      </dds-modal>

      <dds-modal
        modal-id="whenTimelineChanged"
        modal-title="There are unsaved changes."
      >
        <dds-content>
          <div class="mb-3">
            <p id="whenTimelineChangedMsg" class="text-secondary"></p>
          </div>
        </dds-content>
        <dds-modal-button
          button-color="btn-light"
          button-text-color="text-dark"
          is-dismiss="true"
          >Close</dds-modal-button
        >
      </dds-modal>

      <div
        class="modal fade"
        id="shortKey"
        data-bs-keyboard="false"
        tabindex="-1"
      >
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content bg-dark">
            <div class="modal-body">
              <h5 class="modal-title text-white font-weight-lg">Shortcut</h5>
              <div class="mb-3">
                <table class="table table-dark ">
                  <tbody>
                    <tr>
                      <th scope="row">Control C</th>
                      <td class="text-secondary">Copy Element on Timeline</td>
                    </tr>
                    <tr>
                      <th scope="row">Control V</th>
                      <td class="text-secondary">Paste Element on Timeline</td>
                    </tr>
                    <tr>
                      <th scope="row">Control X</th>
                      <td class="text-secondary">Copy & Delete on Timeline</td>
                    </tr>
                    <tr>
                      <th scope="row">Control D</th>
                      <td class="text-secondary">Split Element</td>
                    </tr>
                    <tr>
                      <th scope="row">Control O</th>
                      <td class="text-secondary">Load Project File</td>
                    </tr>
                    <tr>
                      <th scope="row">Control S</th>
                      <td class="text-secondary">Save Project File</td>
                    </tr>
                    <tr>
                      <th scope="row">Backspace</th>
                      <td class="text-secondary">Remove Element</td>
                    </tr>
                    <tr>
                      <th scope="row">Space</th>
                      <td class="text-secondary">Play & Pasue</td>
                    </tr>
                    <tr>
                      <th scope="row">Left & Right Arrow</th>
                      <td class="text-secondary">Move Next & Prev Frame</td>
                    </tr>
                    <tr>
                      <th scope="row">Top & Bottom Arrow</th>
                      <td class="text-secondary">Move Element Top or Bottom</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="modal fade"
        id="changeLang"
        data-bs-keyboard="false"
        tabindex="-1"
      >
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content bg-dark">
            <div class="modal-body">
              <h5 class="modal-title text-white font-weight-lg">
                ${this.lc.t("modal.change_language")}
              </h5>

              <b class="text-secondary"
                ><i class="fas fa-info-circle"></i> ${this.lc.t(
                  "modal.change_language_description",
                )}
              </b>
              <div class="mt-3">
                <div class="flex row mb-3">
                  <button
                    class="btn btn-sm btn-default text-light mt-1"
                    @click=${() => this._handleClickChangeLang("en")}
                  >
                    English
                  </button>

                  <button
                    class="btn btn-sm btn-default text-light mt-1"
                    @click=${() => this._handleClickChangeLang("ko")}
                  >
                    한국어
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="modal fade"
        id="NeedsToRestart"
        data-bs-keyboard="false"
        data-bs-backdrop="static"
        tabindex="-1"
      >
        <div class="modal-dialog modal-dialog-centered modal-lg">
          <div class="modal-content bg-dark">
            <div class="modal-body">
              <h5 class="modal-title text-white font-weight-lg">
                ${this.lc.t("modal.needs_to_restart")}
              </h5>

              <b class="text-danger"
                ><i class="fas fa-info-circle"></i> ${this.lc.t(
                  "modal.needs_to_restart_description",
                )}
              </b>
              <div class="mt-3">
                <div class="flex row mb-3 gap-2">
                  <button
                    type="button"
                    class="col btn btn-secondary"
                    data-bs-dismiss="modal"
                  >
                    ${this.lc.t("modal.close")}
                  </button>
                  <button
                    type="button"
                    @click=${this._handleClickRestart}
                    class="col btn btn-danger"
                  >
                    ${this.lc.t("modal.restart")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
