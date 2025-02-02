import { spawn } from "child_process";
import { mainWindow } from "../main";
import { ipcMain } from "electron";
import { ffmpegConfig } from "../lib/ffmpeg";

let ffmpegProcess;

export function startFFmpegProcess(options, timeline) {
  const ffmpegPath = ffmpegConfig.FFMPEG_PATH;
  const ffprobePath = ffmpegConfig.FFPROBE_PATH;

  const filterComplexArray: string[] = [];
  const mapAudioLists: string[] = [];
  const args: string[] = [];

  args.push("-f", "image2pipe", "-vcodec", "png", "-r", "60", "-i", "pipe:0");

  let index = 0;

  for (const key in timeline) {
    if (Object.prototype.hasOwnProperty.call(timeline, key)) {
      const element = timeline[key];
      if (element.filetype == "video" || element.filetype == "audio") {
        args.push(
          "-ss",
          `${(element.trim.startTime / 1000) * (element.speed || 1)}`,
        );
        args.push(
          "-t",
          `${element.trim.endTime / 1000 - element.trim.startTime / 1000}`,
        );
        args.push("-i", element.localpath);

        const delayMs = Math.round(element.startTime);
        const label = `audio${index}`;
        filterComplexArray.push(
          `[${index + 1}:a]adelay=${delayMs}|${delayMs}[${label}]`,
        );
        mapAudioLists.push(`[${label}]`);
        index += 1;
      }
    }
  }

  if (mapAudioLists.length == 0) {
    filterComplexArray.push(
      `anullsrc=channel_layout=stereo:sample_rate=44100:d=${options.videoDuration}[silent]`,
    );
    mapAudioLists.push(`[silent]`);
  }

  filterComplexArray.push(`[0:v]null[vout]`);

  if (mapAudioLists.length > 1) {
    const amixInput = mapAudioLists.join("");
    filterComplexArray.push(
      `${amixInput}amix=inputs=${mapAudioLists.length}[aout]`,
    );
  } else {
    filterComplexArray.push(`${mapAudioLists[0]}aresample=async=1[aout]`);
  }

  const filterComplex = filterComplexArray.join(";");
  args.push("-filter_complex", filterComplex);

  args.push("-map", "[vout]", "-map", "[aout]");

  args.push(
    "-c:a",
    "aac",
    "-c:v",
    "libx264",
    `-t`,
    `${options.videoDuration}`,
    "-pix_fmt",
    "yuv420p",
    options.videoDestination,
  );

  console.log(args, "EEE");

  ffmpegProcess = spawn(ffmpegPath, args);

  ffmpegProcess.stderr.on("data", (data) => {
    console.log("[ffmpeg]", data.toString());
  });

  ffmpegProcess.on("close", (code) => {
    mainWindow.webContents.send("PROCESSING_FINISH");
  });
}

export const ipcRenderV2 = {
  start: (event, options, timeline) => {
    startFFmpegProcess(options, timeline);
  },
  sendFrame: (event, arrayBuffer) => {
    const buffer = Buffer.from(arrayBuffer);
    console.log("render", new Date());
    if (ffmpegProcess && ffmpegProcess.stdin.writable) {
      ffmpegProcess.stdin.write(buffer);
    }
  },
  finishStream: () => {
    if (ffmpegProcess) {
      ffmpegProcess.stdin.end();
    }
  },
};
