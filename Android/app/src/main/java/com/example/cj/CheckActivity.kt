package com.example.cj

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.net.Uri
import android.util.Log
import android.widget.ImageView
import com.bumptech.glide.Glide
import com.example.cj.databinding.ActivityCheckBinding
import com.example.cj.databinding.ActivityConveyorMainBinding
import com.google.firebase.storage.FirebaseStorage
import java.text.SimpleDateFormat
import java.util.Date


class CheckActivity : AppCompatActivity() {

    private var mBinding : ActivityCheckBinding? = null
    private val binding get() = mBinding!!

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mBinding = ActivityCheckBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val uploadUri = intent.getParcelableExtra<Uri>("img_Uri")
        Log.d("test-uri-log", uploadUri.toString())

        if (uploadUri != null) {
            loadAndDisplayImage(uploadUri)
        } else {
            // Handle the case when uploadUri is null (error occurred during image capture)
        }

        val intent = Intent(this,StopboxMain::class.java)
        val intent2 = Intent(this,StopboxResultActivity::class.java)
        binding.cancleBottomBtn.setOnClickListener { startActivity(intent) }

        binding.okBottomBtn.setOnClickListener{
            //firebase-storage instance
        var storage: FirebaseStorage? = FirebaseStorage.getInstance()

        // file name - 추후에 이미지 크기도 첨가
        var timestamp = SimpleDateFormat("yyyyMMdd_HHmmss").format(Date())
        var fileName = "IMAGE_" + timestamp + "_.jpg"

        // default destination = images/${filename}
        var imagesRef = storage!!.reference.child("stopbox/").child(fileName)
        uploadUri?.let { uri ->
            imagesRef.putFile(uri).addOnSuccessListener {
                //Toast.makeText(activity, getString(R.string.upload_success), Toast.LENGTH_SHORT).show()
            }
        }
            startActivity(intent2)
        }

    }

    private fun loadAndDisplayImage(uploadUri: Uri) {
        Glide.with(this)
            .load(uploadUri)
            .into(binding.imgView)
    }

}