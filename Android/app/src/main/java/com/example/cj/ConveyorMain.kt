package com.example.cj

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.os.Environment
import android.util.Log
import android.widget.Toast
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.net.toUri
import com.example.cj.databinding.ActivityConveyorMainBinding
import com.google.firebase.storage.FirebaseStorage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Timer
import java.util.TimerTask
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.concurrent.scheduleAtFixedRate
import kotlin.concurrent.timerTask

class ConveyorMain : AppCompatActivity() {
    private var mBinding: ActivityConveyorMainBinding? = null
    //매번 null 체크하지 않도록 확인 후 재 선언
    private val binding get() = mBinding!!

    private var preview : Preview? = null
    private var imageCapture: ImageCapture? = null

    private lateinit var outputDirectory: File
    private lateinit var cameraExecutor: ExecutorService

    var uploadUri : Uri? = null
    private var pictureCounter: Int = 0

    // Create a CoroutineScope for managing coroutines
    val coroutineScope = CoroutineScope(Dispatchers.Main)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mBinding = ActivityConveyorMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Set the capture interval (e.g., capture every 5 seconds)
        val captureIntervalMillis = 5000L

        val timer = Timer()
        if (allPermissionsGranted()) {
            startCamera(pictureCounter)
        } else {
            ActivityCompat.requestPermissions(
                this, ConveyorMain.REQUIRED_PERMISSIONS, ConveyorMain.REQUEST_CODE_PERMISSIONS
            )
        }

        binding.cameraCaptureButton.setOnClickListener{
            startCameraCapture()
        }

        outputDirectory = getOutputDirectory()

        cameraExecutor = Executors.newSingleThreadExecutor()

    }

    private fun startCamera(pictureCounter: Int) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            // Used to bind the lifecycle of cameras to the lifecycle owner
            val cameraProvider: ProcessCameraProvider = cameraProviderFuture.get()

            // Preview
            preview = Preview.Builder()
                .build()
                .also {
                    it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
                }
            // ImageCapture
            imageCapture = ImageCapture.Builder()
                .build()

            // Select back camera as a default
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                // Unbind use cases before rebinding
                cameraProvider.unbindAll()

                // Bind use cases to camera
                cameraProvider.bindToLifecycle(
                    this,
                    cameraSelector,
                    preview,
                    imageCapture)

            } catch(exc: Exception) {
                Log.d("CameraX-Debug", "Use case binding failed", exc)
            }

        }, ContextCompat.getMainExecutor(this))
    }

    private fun allPermissionsGranted() = ConveyorMain.REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(
            baseContext, it) == PackageManager.PERMISSION_GRANTED
    }
    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults:
        IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == ConveyorMain.REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera(pictureCounter)
            } else {
                Toast.makeText(this,
                    "Permissions not granted by the user.",
                    Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    // 사진 업로드 함수
    private fun uploadImageToFirebase(imageUri: Uri?,pictureCounter: Int) {
        var storage: FirebaseStorage? = FirebaseStorage.getInstance()

        // file name - 추후에 이미지 크기도 첨가
        var timestamp = SimpleDateFormat("yyyyMMdd_HHmmss").format(Date())
        var fileName = "JPEG_"+timestamp+"$pictureCounter"

        // default destination = images/${filename}
        var imagesRef = storage!!.reference.child("conveyor/").child(fileName)
        uploadUri?.let { uri ->
            imagesRef.putFile(uri).addOnSuccessListener {
                //Toast.makeText(activity, getString(R.string.upload_success), Toast.LENGTH_SHORT).show()
            }
        }
    }

    // 이미지 파일 생성 함수
    private fun createImageFile(pictureCounter: Int): File {
        // 파일 생성 및 파일 경로 반환
        val timeStamp: String = SimpleDateFormat("yyyyMMdd_HHmmss").format(System.currentTimeMillis())
        val imageFileName = "JPEG_${timeStamp}_$pictureCounter"
        val storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        val image = File.createTempFile(imageFileName, ".jpg", storageDir)
        uploadUri = image.toUri()
        return image
    }

    // 사진 촬영 함수
    private fun captureImage(pictureCounter: Int) {
        val outputOptions = ImageCapture.OutputFileOptions.Builder(createImageFile(pictureCounter)).build()
        imageCapture?.takePicture(
            outputOptions, cameraExecutor,
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                    // 사진 촬영 성공 시
                    // 이미지 업로드 호출
                    uploadImageToFirebase(outputFileResults.savedUri,pictureCounter)
                }

                override fun onError(exception: ImageCaptureException) {
                    // 사진 촬영 실패 시 처리
                }
            }
        )
    }

    private fun startCameraCapture() {
        val captureIntervalMillis = 500L
        val delayMillis = 0L // 즉시 시작하도록 함

        // 카메라 촬영 횟수
        val numberOfPicturesToTake = 5

        val timer = Timer()
        timer.scheduleAtFixedRate(delayMillis, captureIntervalMillis) {
            // 매번 사진을 촬영하는 함수 호출
            captureImage(pictureCounter)

            // Increment the picture counter
            pictureCounter++

            // Check if we have captured the desired number of pictures
            if (pictureCounter >= numberOfPicturesToTake) {
                // Cancel the timer if we've taken enough pictures
                timer.cancel()
            }
        }
    }
    private fun getOutputDirectory(): File {
        val mediaDir = externalMediaDirs.firstOrNull()?.let {
            File(it, resources.getString(R.string.app_name)).apply {
                mkdirs()
            }
        }
        return if (mediaDir != null && mediaDir.exists()) mediaDir
        else filesDir
    }

    companion object {
        private const val REQUEST_CODE_PERMISSIONS = 10
        private val REQUIRED_PERMISSIONS =
            mutableListOf (
                Manifest.permission.CAMERA
            ).apply {
                if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
                    add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                }
            }.toTypedArray()
    }
}

