import { renderOptionStore } from "../src/states/renderOptionStore";
import { useTimelineStore } from "../src/states/timelineStore";
import { renderImage } from "../src/features/renderer/image";
import { renderVideoWithWait } from "../src/features/renderer/video";
import { renderGif } from "../src/features/renderer/gif";
import { renderText } from "../src/features/renderer/text";
import { renderShape } from "../src/features/renderer/shape";
import { getLocationEnv } from "../src/functions/getLocationEnv";
import { requestIPCVideoExport } from "../src/features/export/ipc";
import { rendererModal } from "../src/utils/modal";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";

export async function exportVideo(data) {
    const elementControlComponent = document.querySelector("element-control") as any;
    if (!elementControlComponent) {
        console.error("Element control component not found. Make sure the component is loaded first.");
        return false;
    }
    try {
        const optionsWithoutDestination = {
            ...renderOptionStore.getState().options,
            videoDuration: renderOptionStore.getState().options.duration,
            videoBitrate: Number(document.querySelector("#videoBitrate")?.value || 48000),
        };

        const elementRenderers = {
            image: renderImage,
            video: renderVideoWithWait,
            gif: renderGif,
            text: renderText,
            shape: renderShape,
        };
        
        const env = getLocationEnv();
        if (env === "electron") {
            const ipc = window.electronAPI.req;
            const videoDestination = await ipc.dialog.exportVideo();
            if (videoDestination == null) {
                return false;
            }

            const fileExists = await ipc.filesystem.existFile(videoDestination);
            if (fileExists) {
                await ipc.filesystem.removeFile(videoDestination);
            }

            const options = {
                ...optionsWithoutDestination,
                videoDestination,
            };

            await requestIPCVideoExport(
                useTimelineStore.getState().timeline,
                elementRenderers,
                options,
                (currentFrame, totalFrames) => {
                    const progressTo100 = (currentFrame / totalFrames) * 100;
                    document.querySelector("#progress").style.width = `${progressTo100}%`;
                    document.querySelector("#progress").innerHTML = `${Math.round(progressTo100)}%`;
                    rendererModal.progressModal.show();
                }
            );
        } else {
            // Web environment handling
            const tempPath = await window.electronAPI.req.app.getTempPath();
            const renderOptionState = renderOptionStore.getState().options;
            const projectDuration = renderOptionState.duration;
            const projectFolder = tempPath.path;
            const projectRatio = elementControlComponent.previewRatio;
            const previewSizeH = renderOptionState.previewSize.h;
            const previewSizeW = renderOptionState.previewSize.w;
            const backgroundColor = renderOptionState.backgroundColor;
            const videoBitrate = Number(document.querySelector("#videoBitrate")?.value || 48000);
            const uuidKey = uuidv4();

            if (projectFolder === "") {
                document.querySelector("toast-box")?.showToast({ 
                    message: "Select a project folder", 
                    delay: "4000" 
                });
                return false;
            }

            const options = {
                videoDuration: projectDuration,
                videoDestination: `${projectFolder}/${uuidKey}.mp4`,
                videoDestinationFolder: projectFolder,
                videoBitrate: videoBitrate,
                previewRatio: projectRatio,
                backgroundColor: backgroundColor,
                previewSize: {
                    w: previewSizeW,
                    h: previewSizeH,
                },
            };

            let timeline = Object.fromEntries(
                Object.entries(useTimelineStore.getState().timeline).sort(
                    ([, valueA]: any, [, valueB]: any) => valueA.priority - valueB.priority,
                ),
            );

            for (const key in timeline) {
                if (Object.prototype.hasOwnProperty.call(timeline, key)) {
                    timeline[key].localpath = `file:/${timeline[key].localpath}`;
                }
            }

            await axios.post("/api/render", {
                options: options,
                timeline: timeline,
            });
        }
        return true;
    }
    catch (error) {
        console.error("Export failed:", error);
        return false;
    }
}

