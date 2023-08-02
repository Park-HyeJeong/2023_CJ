package com.example.cj

import android.Manifest
import android.app.UiAutomation
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.example.cj.databinding.ActivityStopboxMainBinding
import com.google.firebase.storage.FirebaseStorage
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors


class StopboxMain : AppCompatActivity() {
    // ViewBinding
    lateinit private var binding : ActivityStopboxMainBinding

    private var preview : Preview? = null
    private var imageCapture: ImageCapture? = null

    private lateinit var outputDirectory: File
    private lateinit var cameraExecutor: ExecutorService

    var uploadUri : Uri? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStopboxMainBinding.inflate(layoutInflater)
        val view = binding.root
        setContentView(view)

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS)
        }

        val intent = Intent(this,CheckActivity::class.java)

        binding.cameraCaptureButton.setOnClickListener {
            //비동기 처리 : takePhoto 함수와 intent.putExtra가 실행되는 타이밍 오차로 null로 값이 전달되는 오류 수정
            takePhoto { uploadUri ->
                // Handle the uploadUri here
                if (uploadUri != null) {
                    val intent = Intent(this, CheckActivity::class.java)
                    intent.putExtra("img_Uri", uploadUri)
                    startActivity(intent)
                } else {
                    // Handle the case when uploadUri is null (error occurred during image capture)
                }
            }
        }

        outputDirectory = getOutputDirectory()

        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    private fun takePhoto(completion: (Uri?) -> Unit) {
        // Get a stable reference of the modifiable image capture use case
        val imageCapture = imageCapture ?: return

        // Create time-stamped output file to hold the image
        val photoFile = File(
            outputDirectory,
            newJpgFileName())

        // Create output options object which contains file + metadata
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

        // Set up image capture listener, which is triggered after photo has
        // been taken
        imageCapture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onError(exc: ImageCaptureException) {
                    Log.d("CameraX-Debug", "Photo capture failed: ${exc.message}", exc)
                }

                override fun onImageSaved(output: ImageCapture.OutputFileResults){
                    val savedUri = Uri.fromFile(photoFile)
                    uploadUri = Uri.fromFile(photoFile)
                    val msg = "Photo capture succeeded: $savedUri"
                    Toast.makeText(baseContext, msg, Toast.LENGTH_SHORT).show()
                    Log.d("CameraX-Debug", msg)

                    completion(uploadUri)
                }

            })

    // firebase-storage instance
//        var storage: FirebaseStorage? = FirebaseStorage.getInstance()
//
//        // file name - 추후에 이미지 크기도 첨가
//        var timestamp = SimpleDateFormat("yyyyMMdd_HHmmss").format(Date())
//        var fileName = "IMAGE_" + timestamp + "_.jpg"
//
//        // default destination = images/${filename}
//        var imagesRef = storage!!.reference.child("images/").child(fileName)
//        uploadUri?.let { uri ->
//            imagesRef.putFile(uri).addOnSuccessListener {
//                //Toast.makeText(activity, getString(R.string.upload_success), Toast.LENGTH_SHORT).show()
//            }
//        }
    }

    // viewFinder 설정 : Preview
    private fun startCamera() {
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

    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(
            baseContext, it) == PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults:
        IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera()
            } else {
                Toast.makeText(this,
                    "Permissions not granted by the user.",
                    Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
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


    private fun newJpgFileName() : String {
        val sdf = SimpleDateFormat("yyyyMMdd_HHmmss")
        val filename = sdf.format(System.currentTimeMillis())
        return "${filename}.jpg"
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


}
