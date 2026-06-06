import asyncio
import cv2
import numpy as np
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    try:
        processor = TMDRadarProcessor("kkn240")
        
        # 1. Test Issue 55: Mapping (Landmarks)
        landmarks = {
            "Khon Kaen": (16.4322, 102.8236),
            "Udon Thani": (17.4138, 102.7872),
            "Nakhon Ratchasima": (14.9799, 102.0978),
            "Chaiyaphum": (15.8066, 102.0298),
            "Sakon Nakhon": (17.1607, 104.1486),
            "User Test 2 (17.83N, 102.57E)": (17.839333, 102.572861)
        }

        # --- Testing Loop (680x680) ---
        print("\n--- Testing Loop (680x680) ---")
        print("Fetching kkn240 loop frames...")
        frames = await processor.fetch_loop_gif_and_extract_frames()
        if not frames or len(frames) < 2:
            print("No loop frames fetched.")
        else:
            print("Calculating optical flow for Wind/Movement Verification...")
            flow = processor.calculate_optical_flow(frames)
            
            output_frames = []
            for i, frame in enumerate(frames):
                out_frame = frame.copy()
                
                # Draw landmarks on every frame
                for name, (lat, lng) in landmarks.items():
                    # Draw Flat (Linear)
                    px, py = processor.latlng_to_pixel(lat, lng, is_loop=True, projection="linear")
                    if px is not None and py is not None:
                        cv2.circle(out_frame, (px, py), 5, (0, 0, 255), -1)  # Red for Flat
                        cv2.putText(out_frame, name, (px + 8, py + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                    # Draw Curvature (Azimuthal)
                    px2, py2 = processor.latlng_to_pixel(lat, lng, is_loop=True, projection="azimuthal")
                    if px2 is not None and py2 is not None:
                        cv2.circle(out_frame, (px2, py2), 4, (255, 0, 0), -1)  # Blue for Azimuthal
                        # Draw a line connecting them to show the difference
                        if px is not None and py is not None:
                            cv2.line(out_frame, (px, py), (px2, py2), (255, 255, 255), 1)
                        cv2.putText(out_frame, name, (px + 7, py + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                
                # Draw arrows only on the last frame
                if i == len(frames) - 1:
                    step = 10 
                    drawn_arrows = 0
                    for y in range(0, out_frame.shape[0], step):
                        for x in range(0, out_frame.shape[1], step):
                            vx, vy = processor.get_flow_vector_at(flow, x, y)
                            dbz = processor.get_dbz_at_pixel(frames[-1], x, y)
                            if dbz > 5.0 and (abs(vx) > 0.1 or abs(vy) > 0.1):
                                end_x = int(x + vx * 5) 
                                end_y = int(y + vy * 5)
                                cv2.arrowedLine(out_frame, (x, y), (end_x, end_y), (0, 255, 0), 2, tipLength=0.5)
                                drawn_arrows += 1
                    print(f"Drawn {drawn_arrows} motion vectors (green arrows) on rain cells.")
                
                output_frames.append(out_frame)
            
            import imageio.v3 as iio
            iio.imwrite("backend/tmp/radar_verification_animated.gif", output_frames, duration=500, loop=0)
            print("Success! Animated GIF saved to backend/tmp/radar_verification_animated.gif")

        # --- Testing Static (800x800) ---
        print("\n--- Testing Static (~800x800) ---")
        import imageio.v3 as iio
        print(f"Fetching {processor.config.static_image_url} ...")
        static_img = iio.imread(processor.config.static_image_url)
        if len(static_img.shape) == 4:
            static_frame = static_img[0].copy()
        else:
            static_frame = static_img.copy()
            
        # Convert paletted/RGBA to RGB if needed
        if static_frame.shape[-1] == 4:
            static_frame = cv2.cvtColor(static_frame, cv2.COLOR_RGBA2RGB)
            
        print(f"Static image shape: {static_frame.shape}")
        print("Plotting landmarks for Mapping Verification on Static...")
        for name, (lat, lng) in landmarks.items():
            # Draw Flat (Linear)
            px, py = processor.latlng_to_pixel(lat, lng, is_loop=False, projection="linear")
            if px is not None and py is not None:
                cv2.circle(static_frame, (px, py), 5, (0, 0, 255), -1)  # Red for Flat
                cv2.putText(static_frame, name, (px + 8, py + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # Draw Curvature (Azimuthal)
            px2, py2 = processor.latlng_to_pixel(lat, lng, is_loop=False, projection="azimuthal")
            if px2 is not None and py2 is not None:
                cv2.circle(static_frame, (px2, py2), 4, (255, 0, 0), -1)  # Blue for Azimuthal
                if px is not None and py is not None:
                    cv2.line(static_frame, (px, py), (px2, py2), (255, 255, 255), 1)

        static_frame_bgr = cv2.cvtColor(static_frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("backend/tmp/radar_verification_static.png", static_frame_bgr)
        print("Success! Image saved to backend/tmp/radar_verification_static.png")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
